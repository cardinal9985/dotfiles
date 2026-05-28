{
  description = "nostromo system configuration";

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
  };

  outputs = { self, nixpkgs, impermanence, disko, sops-nix, home-manager, nur, ... }@inputs:
  let
    mkHost = { host, user, system ? "x86_64-linux" }: nixpkgs.lib.nixosSystem {
      inherit system;
      specialArgs = { inherit host user inputs; };
      modules = [
        disko.nixosModules.disko
        impermanence.nixosModules.impermanence
        home-manager.nixosModules.home-manager
        nur.modules.nixos.default
        {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;
          home-manager.extraSpecialArgs = { inherit host user inputs; };
          home-manager.users.${user} = import ./home/${user}/${host}.nix;
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
