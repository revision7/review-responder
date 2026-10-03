# Changelog

Release notes based on the project's current documented features.

## [0.1.0]

### Added

- Generate review replies from CSV uploads, pasted text, or Google Business
  Profile reviews.
- Use Claude for brand-aware drafts, with built-in templates available when no
  Anthropic API key is configured.
- Configure tone, reply length, sign-off, escalation rules, and example replies
  in `brand.yaml`.
- Review sentiment and follow-up flags alongside each draft, then edit, copy,
  export, or post replies after approval.
- Try the Google workflow with demo reviews before connecting a live profile.

### Improved

- Keep a batch moving when an individual reply fails, and show the failure on
  the affected review instead of losing the other drafts.
- Reject CSV uploads larger than 2 MB and limit generation requests to 100
  reviews.
- Skip Google reviews that already have a reply.
