"""Agent runtime (Phase 8).

The brain that turns *an agent + a conversation + a new user message*
into a persisted assistant reply. It is deliberately stateless about
HTTP: the API layer owns persistence/commits and audit; the runtime owns
prompt assembly, knowledge retrieval, model invocation, token accounting
and title generation.

Storage mapping
---------------
The AI-chat surface speaks ``role`` (system/user/assistant/tool); the
underlying ``messages`` table speaks ``sender``
(agent/customer/system/tool). The two enums are bridged here so the rest
of Phase 8 can stay role-native without a schema rewrite.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from typing import AsyncIterator, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.agent import Agent
from app.database.models.message import Message, MessageSender
from app.middleware.org_context import OrgContext
from app.providers import AIResponse, ChatMessage, DEFAULT_MODEL, get_provider
from app.services import model_router_service, rag_service
from app.services.rag_service import RetrievedChunk

log = logging.getLogger("app.agent_runtime")

# How many prior messages to replay into the model by default.
DEFAULT_HISTORY_LIMIT = 20
# Knowledge retrieval knobs — kept small to avoid prompt explosion.
DEFAULT_TOP_K = 5
MAX_CONTEXT_CHARS = 4000

# role (API) <-> sender (DB) bridge
ROLE_TO_SENDER: dict[str, MessageSender] = {
    "user": MessageSender.customer,
    "assistant": MessageSender.agent,
    "system": MessageSender.system,
    "tool": MessageSender.tool,
}
SENDER_TO_ROLE: dict[MessageSender, str] = {
    MessageSender.customer: "user",
    MessageSender.agent: "assistant",
    MessageSender.system: "system",
    MessageSender.tool: "tool",
}


def sender_to_role(sender: MessageSender) -> str:
    return SENDER_TO_ROLE.get(sender, "user")


def role_to_sender(role: str) -> MessageSender:
    return ROLE_TO_SENDER.get(role, MessageSender.customer)


class AgentRuntime:
    """Per-request runtime bound to a tenant + DB session."""

    def __init__(self, session: AsyncSession, ctx: OrgContext) -> None:
        self.session = session
        self.ctx = ctx
        self.provider = get_provider()

    # ───────────────────────── agent loading ─────────────────────────

    async def load_agent(self, agent_id: uuid.UUID) -> Optional[Agent]:
        """Org-scoped agent fetch with its 1:1 config eagerly loaded."""
        q = (
            select(Agent)
            .options(selectinload(Agent.config))
            .where(Agent.id == agent_id)
            .where(Agent.organization_id == self.ctx.organization_id)
            .where(Agent.deleted_at.is_(None))
        )
        return await self.session.scalar(q)

    # ───────────────────────── prompt assembly ───────────────────────

    def build_system_prompt(
        self, agent: Agent, context_chunks: Optional[list[str]] = None
    ) -> str:
        cfg = agent.config
        parts: list[str] = []
        parts.append(f"You are {agent.name}, an AI assistant.")
        if agent.description:
            parts.append(agent.description.strip())
        if cfg and cfg.system_prompt:
            parts.append(cfg.system_prompt.strip())
        if cfg and cfg.greeting:
            parts.append(f"Your default greeting is: {cfg.greeting.strip()}")
        if cfg and cfg.language:
            parts.append(f"Always respond in {cfg.language}.")
        if cfg and cfg.voice:
            parts.append(f"Adopt a {cfg.voice} tone.")
        parts.append(
            "Be helpful, accurate and concise. If you are unsure, say so "
            "rather than inventing facts."
        )

        if context_chunks:
            joined = "\n\n".join(context_chunks)
            parts.append(
                "Use the following CONTEXT from the knowledge base to answer "
                "the question. Prefer the context over your own knowledge, and "
                "cite the source document when you use it. If the answer is not "
                "in the context, say you don't have that information.\n\n"
                "CONTEXT:\n" + joined
            )
        return "\n\n".join(parts)

    # ───────────────────────── history loading ───────────────────────

    async def load_history(
        self, conversation_id: uuid.UUID, *, limit: int = DEFAULT_HISTORY_LIMIT
    ) -> list[Message]:
        """Most-recent ``limit`` messages, returned oldest→newest."""
        q = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = list((await self.session.scalars(q)).all())
        rows.reverse()
        return rows

    # ─────────────────────── knowledge retrieval ─────────────────────

    def _linked_kb_ids(self, agent: Agent) -> Optional[list[uuid.UUID]]:
        """KB ids linked to the agent via ``agent_configs.config``.

        Returns ``None`` when no explicit link exists — the caller then
        falls back to *all* active KBs in the org.
        """
        cfg = agent.config
        if not cfg or not isinstance(cfg.config, dict):
            return None
        raw = cfg.config.get("knowledge_base_ids")
        if not raw:
            return None
        out: list[uuid.UUID] = []
        for v in raw:
            try:
                out.append(uuid.UUID(str(v)))
            except (ValueError, TypeError):
                continue
        return out or None

    async def retrieve_context(
        self, agent: Agent, query: str, *, top_k: int = DEFAULT_TOP_K
    ) -> list[RetrievedChunk]:
        """Vector-retrieve the most relevant chunks for ``query``.

        Tenant-scoped through ``documents.organization_id`` (Phase 5). Uses
        pgvector cosine similarity via :mod:`app.services.rag_service`, with
        a keyword fallback baked into that service.
        """
        kb_ids = self._linked_kb_ids(agent)
        return await rag_service.search_chunks(
            self.session,
            query,
            self.ctx.organization_id,
            knowledge_base_ids=kb_ids,
            top_k=top_k,
        )

    # ─────────────────────── message assembly ────────────────────────

    def _to_chat_messages(
        self,
        agent: Agent,
        history: list[Message],
        user_content: str,
        context_blocks: Optional[list[str]],
    ) -> list[ChatMessage]:
        msgs: list[ChatMessage] = [
            ChatMessage(role="system", content=self.build_system_prompt(agent, context_blocks))
        ]
        for m in history:
            role = sender_to_role(m.sender)
            if role == "system":
                continue  # system turns are reconstructed each call
            msgs.append(ChatMessage(role=role, content=m.message))
        msgs.append(ChatMessage(role="user", content=user_content))
        return msgs

    async def build_payload(
        self,
        agent: Agent,
        conversation_id: uuid.UUID,
        user_content: str,
        *,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        use_knowledge: bool = True,
    ) -> tuple[list[ChatMessage], list[RetrievedChunk]]:
        history = await self.load_history(conversation_id, limit=history_limit)
        retrieved: list[RetrievedChunk] = (
            await self.retrieve_context(agent, user_content) if use_knowledge else []
        )
        context_block = (
            [rag_service.build_context(retrieved, max_chars=MAX_CONTEXT_CHARS)]
            if retrieved
            else None
        )
        messages = self._to_chat_messages(agent, history, user_content, context_block)
        return messages, retrieved

    # ───────────────────────── generation ────────────────────────────

    def _model_params(self, agent: Agent) -> tuple[str, float, int]:
        cfg = agent.config
        # A deployment can pin every agent to a single provider model via
        # ``AI_FORCE_MODEL`` (e.g. when the backing provider only serves one
        # model family, such as Amazon Bedrock gpt-oss). When unset, the
        # agent's own configured model is used.
        forced = os.environ.get("AI_FORCE_MODEL", "").strip()
        model = forced or agent.model or DEFAULT_MODEL
        temperature = float(cfg.temperature) if cfg and cfg.temperature is not None else 0.7
        configured_max = cfg.max_tokens if cfg and cfg.max_tokens else 1024
        hard_max = int(os.environ.get("AI_MAX_OUTPUT_TOKENS", "2048"))
        max_tokens = max(1, min(int(configured_max), hard_max))
        return model, temperature, max_tokens

    async def _route_model(self, model: str) -> str:
        """Resolve the effective model via the org's routing policy.

        A deployment-level ``AI_FORCE_MODEL`` pin always wins and bypasses
        the router. Routing failures degrade gracefully to the requested
        model so a policy issue never blocks a reply.
        """
        if os.environ.get("AI_FORCE_MODEL", "").strip():
            return model
        try:
            return await model_router_service.resolve(
                self.session, self.ctx.organization_id, model
            )
        except Exception as e:  # pragma: no cover - defensive
            log.warning("model routing failed (%s); using %s", e, model)
            return model

    async def _route_chain(self, model: str) -> list[str]:
        """The ordered model chain to try: primary first, fallbacks after.

        Honours an ``AI_FORCE_MODEL`` pin (single-item chain) and degrades
        to ``[model]`` if the router can't be consulted.
        """
        if os.environ.get("AI_FORCE_MODEL", "").strip():
            return [model]
        try:
            chain = await model_router_service.ordered_chain(
                self.session, self.ctx.organization_id, model
            )
            return chain or [model]
        except Exception as e:  # pragma: no cover - defensive
            log.warning("model routing failed (%s); using %s", e, model)
            return [model]

    async def generate_reply(
        self, agent: Agent, messages: list[ChatMessage]
    ) -> AIResponse:
        """Invoke the configured model provider with model-level fallback:

        1. **Model fallback** — try each model in the routed chain (same
           provider, e.g. a cheaper/faster model if the primary is
           overloaded).
        Provider outages are surfaced to the API caller. Production must never
        persist a fabricated assistant response as if a model answered.
        """
        model, temperature, max_tokens = self._model_params(agent)
        chain = await self._route_chain(model)
        last_error: Optional[Exception] = None
        for idx, candidate in enumerate(chain):
            try:
                return await self.provider.chat(
                    messages,
                    model=candidate,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:  # try the next model in the fallback chain
                last_error = e
                nxt = chain[idx + 1] if idx + 1 < len(chain) else None
                log.warning(
                    "model '%s' failed (%s); %s",
                    candidate,
                    e,
                    f"falling back to '{nxt}'" if nxt else "no fallback left",
                )

        # Chain exhausted: surface the original provider error.
        assert last_error is not None
        raise last_error

    async def stream_reply(
        self, agent: Agent, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        model, temperature, max_tokens = self._model_params(agent)
        model = await self._route_model(model)
        async for piece in self.provider.stream(
            messages, model=model, temperature=temperature, max_tokens=max_tokens
        ):
            yield piece

    # ───────────────────────── title generation ──────────────────────

    async def generate_title(self, first_user_message: str) -> str:
        """Short, human title derived from the first user message.

        Tries the model; falls back to a deterministic truncation so a
        title is *always* produced (the audit checks for one).
        """
        text = (first_user_message or "").strip()
        if not text:
            return "New Conversation"
        try:
            prompt = [
                ChatMessage(
                    role="system",
                    content=(
                        "Generate a concise 3-6 word title for a chat that "
                        "starts with the user's message. Reply with the title "
                        "only — no quotes, no punctuation at the end."
                    ),
                ),
                ChatMessage(role="user", content=text[:500]),
            ]
            resp = await self.provider.chat(
                prompt, model=DEFAULT_MODEL, temperature=0.3, max_tokens=20
            )
            title = resp.content.strip().strip('"').strip()
            title = re.sub(r"\s+", " ", title)
            if title:
                return title[:80]
        except Exception as e:  # noqa: BLE001 — title is best-effort
            log.info("title generation fell back to heuristic: %s", e)
        words = text.split()
        return (" ".join(words[:6]) + ("…" if len(words) > 6 else ""))[:80]
