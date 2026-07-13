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

  };

  home.file.".config/chromium/policies/managed/policy.json".text = builtins.toJSON {
    BrowserSignin             = 0;
    SyncDisabled              = true;
    MetricsReportingEnabled   = false;
    SafeBrowsingProtectionLevel = 0;
    SafeBrowsingExtendedReportingOptInAllowed = false;
    NetworkPredictionOptions  = 2;
    BuiltInDnsClientEnabled   = false;
    AlternateErrorPagesEnabled = false;
    PasswordManagerEnabled    = false;
    AutofillAddressEnabled    = false;
    AutofillCreditCardEnabled = false;
    TranslateEnabled          = false;
    SpellcheckEnabled         = false;
    SearchSuggestEnabled      = false;
    BackgroundModeEnabled     = false;
    DownloadDirectory         = "/home/maxwell/downloads/browser";
    DefaultSearchProviderEnabled   = true;
    DefaultSearchProviderName      = "Degoog";
    DefaultSearchProviderSearchURL = "https://search.ishimura.lol/search?q={searchTerms}";
  };
}
