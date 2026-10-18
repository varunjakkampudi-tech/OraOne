# Public media review

Status: **not visually reviewed.** No image was opened or inspected for this review. The findings below come only from the file list, the generation prompts in `scripts/generate-images.ts` (which ask for no text, logos or human faces), and the page usage in `src/components/site/images.ts` and `src/components/site/templates.tsx`. A visual check by the owner is still required before launch.

## Images used on the public site

These generated images are referenced by the public site through `solutionImage()`, shown on the solution cards that link to:

| File                                           | Used on                                        | Prompt asks for                              | Action                                                 |
| ---------------------------------------------- | ---------------------------------------------- | -------------------------------------------- | ------------------------------------------------------ |
| `public/media/generated/solution-support.webp` | Solution card to `/solutions/customer-support` | Help-centre book, question mark, chat bubble | Owner to confirm visually. No person or logo expected. |
| `public/media/generated/solution-leads.webp`   | Solution card to `/solutions/lead-generation`  | Glass funnel with dots                       | Owner to confirm visually.                             |
| `public/media/generated/solution-sales.webp`   | Solution card to `/solutions/sales`            | Rising light line over tiles                 | Owner to confirm visually.                             |
| `public/media/generated/solution-small.webp`   | Solution card to `/solutions/small-business`   | Storefront with open sign                    | Owner to confirm visually.                             |

No image in this list is known to show a person or a client logo, so no replacement is recommended on current evidence. Generated images can still contain unrequested details, so the owner should look at all four before launch.

## Generated images not referenced by the public site

These files exist in `public/media/generated` but no source file references them (checked by searching `src/`, `docs/` and `e2e/`):

- `hero-home.webp`, `hero-product.webp`
- `feature-widget.webp`, `feature-knowledge.webp`, `feature-inbox.webp`, `feature-leads.webp`
- `use-dental.webp`, `use-plumbing.webp`, `use-fitness.webp`, `use-shop.webp`, `use-legal.webp`, `use-letting.webp`
- `about-mission.webp`

They are not visible to visitors. They are left in place (not deleted). Do not reference them on a public page until the owner has viewed them.

## Related files outside this set

The product screens `public/media/studio-inbox.jpg`, `studio-install.jpg`, `studio-assistant-editor.jpg`, `studio-knowledge.jpg` and `studio-leads.jpg` are captures of the running app shown in the public product page (`templates.tsx`). They are not generated images and were not reviewed here. Because they are captures of sample data, the owner should check that they show no real names, phone numbers or email addresses.
