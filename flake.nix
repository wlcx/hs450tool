{
  description = "A basic flake from samw";
  inputs = {
    utils.url = "github:numtide/flake-utils";
    devshell.url = "github:numtide/devshell";
  };
  outputs = {
    self,
    nixpkgs,
    utils,
    devshell,
  }:
    utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {
        inherit system;

        overlays = [devshell.overlays.default];
      };
    in {
      devShells.default = pkgs.devshell.mkShell {
        packages = with pkgs; [
          ruff
          (python3.withPackages (p: [ p.tkinter p.pillow p.numpy p.snakeviz ]))
          /*(pkgs.memray.overrideAttrs (prev: {
            src = fetchFromGitHub {
              owner = "bloomberg";
              repo = "memray";
              rev = "refs/tags/v1.12.0";
              hash = "sha256-H78IZuRbpt9W3R4Rj7Y01TwuU5BWe+aaUcLmNr5JXIA=";
            };
            format = "pyproject";
            buildInputs = prev.buildInputs ++ [pkgs.python3.pkgs.pkgconfig];
            meta.platforms = lib.platforms.darwin;
            NIX_CFLAGS_COMPILE = lib.optionals (stdenv.cc.isClang && stdenv.isDarwin) [
              "-fno-lto"  # work around https://github.com/NixOS/nixpkgs/issues/19098
            ];
            preBuild = lib.optionalString (stdenv.isDarwin ) ''
              export CMAKE_ARGS="-DCMAKE_CXX_COMPILER_AR=$AR -DCMAKE_CXX_COMPILER_RANLIB=$RANLIB"
            '';
          }))*/
        ];
      };
      formatter = pkgs.alejandra;
    });
}
