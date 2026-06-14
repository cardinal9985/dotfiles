{ pkgs, ... }:

let
  # Grafana Alloy config in River language. Ships the systemd journal
  # to Loki on ishimura via MagicDNS so tailnet IP drift is harmless.
  # Replaces the EOL promtail (deprecated in nixpkgs 26.05).
  alloyConfig = pkgs.writeText "config.alloy" ''
    loki.relabel "journal" {
      forward_to = []

      rule {
        source_labels = ["__journal__systemd_unit"]
        target_label  = "unit"
      }
      rule {
        source_labels = ["__journal__hostname"]
        target_label  = "host"
      }
      rule {
        source_labels = ["__journal_priority_keyword"]
        target_label  = "priority"
      }
    }

    loki.source.journal "default" {
      max_age       = "12h"
      relabel_rules = loki.relabel.journal.rules
      labels        = {
        job = "systemd-journal",
      }
      forward_to = [loki.write.ishimura.receiver]
    }

    loki.write "ishimura" {
      endpoint {
        url = "http://ishimura:3100/loki/api/v1/push"
      }
    }
  '';
in
{
  services.alloy = {
    enable = true;
    configPath = alloyConfig;
  };
}
