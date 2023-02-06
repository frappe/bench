{
  description = "CLI to manage Multi-tenant deployments for Frappe apps";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

  outputs = {nixpkgs, self}: let
    perSystem = f: builtins.mapAttrs (_: f) nixpkgs.legacyPackages;
  in {
    packages = perSystem (pkgs: rec {
      default = bench;
      bench = with pkgs;
        python3.pkgs.buildPythonApplication rec {
          pname = "bench";
          version =
            builtins.head (
              builtins.match
                ''^VERSION = "([^"]+).*''
                (builtins.readFile ./bench/__init__.py)
            );
          format = "pyproject";
        
          src = ./.;
        
          postPatch = ''
            substituteInPlace pyproject.toml \
              --replace 'Jinja2~=3.0.3' 'Jinja2' \
              --replace 'python-crontab~=2.6.0' 'python-crontab' \
              --replace 'semantic-version~=2.8.2' 'semantic-version'
          '';

          # signal to bench that it's executed from a nix wrapper
          # with the full pythen & bin environment already set up
          makeWrapperArgs = "--set NIX_WRAPPED 1";

        
          propagatedBuildInputs = [
            coreutils
            gitMinimal
            # non-python runtime deps
            redis
            nodejs
            mariadb
            postgresql
            yarn
            cron
            # wkhtmltopdf - has unmaintained dep; pdf printing not available out of the box
            # https://github.com/frappe/bench/issues/1427
            nginx
          ] ++ (with python3.pkgs; [
            # for bench's own environment management
            pip
            supervisor
            psutil
            # other
            click
            gitpython
            python-crontab
            requests
            semantic-version
            setuptools
            tomli
            # python; but not in pythonPackages
            honcho
            staticjinja
          ]);
        
          nativeBuildInputs = with python3.pkgs; [
            hatchling
          ];
        
          pythonImportsCheck = [ "bench" ];
        
          meta = with lib; {
            description = "CLI to manage Multi-tenant deployments for Frappe apps";
            homepage = "https://github.com/frappe/bench";
            license = with licenses; [ gpl3 ];
            maintainers = with maintainers; [ ];
          };
        };

    });
  };
}
