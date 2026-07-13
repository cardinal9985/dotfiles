{ ... }:

{
  programs.chromium = {
    enable = true;

    commandLineArgs = [
      "--no-default-browser-check"
      "--no-first-run"
      "--disable-background-networking"
      "--disable-client-side-phishing-detection"
    ];

    extensions = [
      { id = "ddkjiahejlhfcafbddmgiahcphecmpfh"; } # uBlock Origin Lite
      { id = "mnjggcdmjocbbbhaepdhchncahnbgone"; } # SponsorBlock
    ];

    extraOpts = {
      # ── Account + Sync ──────────────────────────────────────────────
      "BrowserSignin"             = 0;     # disable sign-in entirely
      "SyncDisabled"              = true;

      # ── Telemetry + Reporting ────────────────────────────────────────
      "MetricsReportingEnabled"   = false;
      "SafeBrowsingProtectionLevel" = 0;   # disable (sends URL hashes to Google)
      "SafeBrowsingExtendedReportingOptInAllowed" = false;

      # ── Network ──────────────────────────────────────────────────────
      "NetworkPredictionOptions"  = 2;     # never prefetch DNS or preconnect
      "BuiltInDnsClientEnabled"   = false; # use system DNS so AdGuard applies
      "AlternateErrorPagesEnabled" = false; # don't use Google for error pages

      # ── Autofill + Passwords ─────────────────────────────────────────
      "PasswordManagerEnabled"    = false;
      "AutofillAddressEnabled"    = false;
      "AutofillCreditCardEnabled" = false;

      # ── UI Noise ─────────────────────────────────────────────────────
      "TranslateEnabled"          = false;
      "SpellcheckEnabled"         = false;
      "SearchSuggestEnabled"      = false;
      "BackgroundModeEnabled"     = false;

      # ── Default Search: SearXNG ──────────────────────────────────────
      "DefaultSearchProviderEnabled"   = true;
      "DefaultSearchProviderName"      = "Degoog";
      "DefaultSearchProviderSearchURL" = "https://search.ishimura.lol/search?q={searchTerms}";
    };
  };
}
