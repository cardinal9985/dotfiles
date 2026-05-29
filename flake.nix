{
  description = "My System Configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

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
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nur = {
      url = "github:nix-community/NUR";
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
  };

  outputs = { self, nixpkgs, impermanence, disko, sops-nix, home-manager, nur, nixcord, stylix, ... }@inputs:
  let
    mkHost = { host, user, system ? "x86_64-linux" }: nixpkgs.lib.nixosSystem {
      inherit system;
      specialArgs = { inherit host user inputs; };
      modules = [
        disko.nixosModules.disko
        impermanence.nixosModules.impermanence
        home-manager.nixosModules.home-manager
        nur.modules.nixos.default
        stylix.nixosModules.stylix
        {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;
          home-manager.backupFileExtension = "backup";
          home-manager.extraSpecialArgs = { inherit host user inputs; };
          home-manager.users.${user} = import ./home/${user}/${host}.nix;
          home-manager.sharedModules = [ nixcord.homeModules.default ];
        }
        ./hosts/${host}/disko.nix
        ./hosts/${host}/hardware-configuration.nix
        ./hosts/${host}/configuration.nix
      ];
    };
  in {
    nixosConfigurations = {
      nostromo = mkHost { host = "nostromo"; user = "maxwell"; };
    };
  };
}
