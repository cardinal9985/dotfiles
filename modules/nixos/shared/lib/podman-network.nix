{ pkgs, lib }:
{ name, containers, subnet ? null, disableDns ? true }:
let
  args = lib.concatStringsSep " " (
    lib.optional disableDns "--disable-dns" ++
    lib.optional (subnet != null) "--subnet=${subnet}"
  );
  argsStr  = if args != "" then " ${args}" else "";
  svcName  = "create-${name}-network";
in
lib.mkMerge ([
  {
    systemd.services.${svcName} = {
      description = "Create ${name} podman network";
      wantedBy    = map (c: "podman-${c}.service") containers;
      before      = map (c: "podman-${c}.service") containers;
      after       = [ "podman.service" ];
      serviceConfig = {
        Type            = "oneshot";
        RemainAfterExit = true;
      };
      script = ''
        ${pkgs.podman}/bin/podman network exists ${name} || \
          ${pkgs.podman}/bin/podman network create${argsStr} ${name}
      '';
    };
  }
] ++ map (c: {
  systemd.services."podman-${c}".after = [ "${svcName}.service" ];
}) containers)
