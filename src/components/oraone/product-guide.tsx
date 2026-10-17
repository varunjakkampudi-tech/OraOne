// Plain-language guide shown on a /studio screen. Copy describes what the code does today.
// Use it directly under the screen's PageHeader (or its h1).

export type ProductGuideTerm = {
  /** The label as the screen shows it, for example "Connected" or "Already a lead". */
  term: string;
  /** One short sentence in plain language. */
  meaning: string;
};

export type ProductGuideProps = {
  /** One or two short sentences describing what the screen is for. */
  whatItDoes: string;
  /** Things the business needs before this screen works. Each item is one short sentence. */
  needs: readonly [string, ...string[]];
  /** Optional labelled meanings for statuses, channels, or outcomes shown on the screen. */
  terms?: readonly ProductGuideTerm[];
  /** Heading above the terms. Defaults to "Key terms". */
  termsHeading?: string;
};

export function ProductGuide({
  whatItDoes,
  needs,
  terms = [],
  termsHeading = "Key terms",
}: ProductGuideProps) {
  return (
    <section
      aria-label="About this screen"
      className="mt-6 grid gap-5 rounded-xl border border-border bg-card p-4 text-sm sm:p-5"
    >
      <div className="grid gap-1">
        <h2 className="font-semibold">What this does</h2>
        <p className="text-muted-foreground">{whatItDoes}</p>
      </div>

      <div className="grid gap-1">
        <h2 className="font-semibold">What you need before it works</h2>
        <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
          {needs.map((need) => (
            <li key={need}>{need}</li>
          ))}
        </ul>
      </div>

      {terms.length > 0 && (
        <div className="grid gap-2">
          <h2 className="font-semibold">{termsHeading}</h2>
          <dl className="grid gap-3 sm:grid-cols-2">
            {terms.map((item) => (
              <div key={item.term} className="grid gap-0.5">
                <dt className="font-medium">{item.term}</dt>
                <dd className="text-muted-foreground">{item.meaning}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </section>
  );
}
