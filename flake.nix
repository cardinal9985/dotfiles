{
  description = "My System Configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    colmena = {
      url = "github:zhaofengli/colmena";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    impermanence.url = "github:nix-community/impermanence";

    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    sops-nix = {
      url = "github:mic92/sops-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nix-mineral = {
      url = "github:cynicsketch/nix-mineral";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nix-citizen = {
      url = "github:LovingMelody/nix-citizen";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nur = {
      url = "github:nix-community/NUR";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    spicetify-nix = {
      url = "github:Gerg-L/spicetify-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nixcord = {
      url = "github:kaylorben/nixcord";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    stylix = {
      url = "github:danth/stylix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    zen-browser = {
      url = "github:0xc000022070/zen-browser-flake";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    rocksmith-nix = {
      url = "github:Daaboulex/rocksmith-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nix-index-database = {
      url = "github:nix-community/nix-index-database";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    hangar = {
      url = "git+ssh://git@github.com/cardinal9985/hangar";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    loadout = {
      url = "git+ssh://git@github.com/cardinal9985/loadout";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    refinery = {
      url = "git+ssh://git@github.com/cardinal9985/refinery";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    stats = {
      url = "git+ssh://git@github.com/cardinal9985/stats";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    requests = {
      url = "git+ssh://git@github.com/cardinal9985/requests";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    bridge = {
      url = "git+ssh://git@github.com/cardinal9985/bridge";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    rec-room = {
      url = "git+ssh://git@github.com/cardinal9985/rec-room";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    homepage = {
      url = "git+ssh://git@github.com/cardinal9985/homepage";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    daily = {
      url = "git+file:///home/maxwell/projects/daily";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nix-gaming = {
      url = "github:fufexan/nix-gaming";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      colmena,
      impermanence,
      disko,
      sops-nix,
      home-manager,
      nur,
      nixcord,
      stylix,
      spicetify-nix,
      nix-mineral,
      zen-browser,
      nix-citizen,
      rocksmith-nix,
      nix-index-database,
      nix-gaming,
      ...
    }@inputs:
    let
      system = "x86_64-linux";

      workstationModules = { host, user }: [
        disko.nixosModules.disko
        nix-mineral.nixosModules.nix-mineral
        impermanence.nixosModules.impermanence
        home-manager.nixosModules.home-manager
        nur.modules.nixos.default
        stylix.nixosModules.stylix
        {
          nixpkgs.overlays = [
            (import ./overlays/deskmat.nix)
            (import ./overlays/cakewallet.nix)
            rocksmith-nix.overlays.default
          ];
        }
        {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;
          home-manager.backupFileExtension = "backup";
          home-manager.extraSpecialArgs = { inherit host user inputs; };
          home-manager.users.${user} = import ./home/${user}/${host}.nix;
          home-manager.sharedModules = [
            nixcord.homeModules.default
            spicetify-nix.homeManagerModules.default
            zen-browser.homeModules.default
            rocksmith-nix.homeManagerModules.default
            nix-index-database.homeModules.nix-index
          ];
        }
        ./hosts/${host}/disko.nix
        ./hosts/${host}/hardware-configuration.nix
        ./hosts/${host}/configuration.nix
      ];

      serverModules = { host, user }: [
        disko.nixosModules.disko
        impermanence.nixosModules.impermanence
        sops-nix.nixosModules.sops
        home-manager.nixosModules.home-manager
        {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;
          home-manager.backupFileExtension = "backup";
          home-manager.extraSpecialArgs = { inherit host user inputs; };
          home-manager.users.${user} = import ./home/${user}/${host}.nix;
          home-manager.sharedModules = [
            nix-index-database.homeModules.nix-index
          ];
        }
        ./hosts/${host}/disko.nix
        ./hosts/${host}/hardware-configuration.nix
        ./hosts/${host}/configuration.nix
      ];

      mkWorkstation =
        { host, user }:
        nixpkgs.lib.nixosSystem {
          inherit system;
          specialArgs = { inherit host user inputs; };
          modules = workstationModules { inherit host user; };
        };

      mkServer =
        { host, user }:
        nixpkgs.lib.nixosSystem {
          inherit system;
          specialArgs = { inherit host user inputs; };
          modules = serverModules { inherit host user; };
        };
    in
    {
      nixosConfigurations = {
        nostromo = mkWorkstation {
          host = "nostromo";
          user = "maxwell";
        };
        ishimura = mkServer {
          host = "ishimura";
          user = "maxwell";
        };
        normandy = mkServer {
          host = "normandy";
          user = "maxwell";
        };
      };

      colmena = {
        meta = {
          nixpkgs = import nixpkgs { inherit system; };
          specialArgs = { inherit inputs; };
        };

        nostromo = { ... }: {
          deployment = {
            targetHost = "192.168.254.87";
            targetPort = 36475;
            targetUser = "maxwell";
            tags = [ "workstation" ];
          };
          imports = workstationModules {
            host = "nostromo";
            user = "maxwell";
          };
        };

        ishimura = { ... }: {
          deployment = {
            targetHost = "192.168.254.186";
            targetPort = 36475;
            targetUser = "maxwell";
            tags = [ "server" ];
          };
          imports = serverModules {
            host = "ishimura";
            user = "maxwell";
          };
        };

        normandy = { ... }: {
          deployment = {
            targetHost = "100.108.98.70";
            targetPort = 36475;
            targetUser = "maxwell";
            tags = [ "server" ];
          };
          imports = serverModules {
            host = "normandy";
            user = "maxwell";
          };
        };
      };
    };
}
