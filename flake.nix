{
  description = "ResolveMe Ticketing System - Nix Contract Definition";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Define the Python environment with required dependencies for the Django project.
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          django
          faker
          coverage
          pillow
        ]);

        # Helper function to easily create bash scripts as Nix apps
        mkApp = name: script: {
          type = "app";
          program = "${pkgs.writeShellScriptBin name script}/bin/${name}";
        };

      in
      {
        apps = {

          # Applies database migrations and seeds the application.
          init = mkApp "init" ''
            echo "Initializing ResolveMe project..."
            ${pythonEnv}/bin/python manage.py makemigrations
            ${pythonEnv}/bin/python manage.py migrate
            echo "Seeding database with realistic scale data..."
            ${pythonEnv}/bin/python manage.py seed
            echo "Initialization complete."
          '';

          # Starts the application and provides access instructions.
          run = mkApp "run" ''
            echo "Starting Django development server..."
            echo "---------------------------------------------------"
            echo "Access the application at: http://localhost:8000"
            echo "---------------------------------------------------"
            ${pythonEnv}/bin/python manage.py runserver 8000
          '';

          # Runs tests non-interactively and generates coverage reports.
          tests = mkApp "tests" ''
            echo "Running automated tests with coverage..."
            ${pythonEnv}/bin/coverage run manage.py test
            
            echo "Generating coverage reports..."
            ${pythonEnv}/bin/coverage xml -o coverage.xml
            ${pythonEnv}/bin/coverage report
            
            echo "---------------------------------------------------"
            echo "Coverage XML written to: ./coverage.xml"
            echo "---------------------------------------------------"
          '';

          # Removes user and seed data.
          unseed = mkApp "unseed" ''
            echo "Unseeding database..."
            ${pythonEnv}/bin/python manage.py unseed
          '';

          # Seeds the database (designed not to fail if already seeded in your custom command).
          seed = mkApp "seed" ''
            echo "Seeding database..."
            ${pythonEnv}/bin/python manage.py seed
          '';

          # Set default app if someone runs `nix run` without a target
          default = self.apps.${system}.run;
        };

        # Provides the Python environment and prints a usage banner upon entering.
        devShells.default = pkgs.mkShell {
          buildInputs = [ pythonEnv ];

          shellHook = ''
            echo "======================================================="
            echo "          ResolveMe Development Environment"
            echo "======================================================="
            echo "Available Nix entrypoints (as per marking contract):"
            echo "  nix run .#init    - Install/configure tools and seed data"
            echo "  nix run .#run     - Start the web application (localhost:8000)"
            echo "  nix run .#tests   - Run tests and generate coverage report"
            echo "  nix run .#seed    - Seed the database with random data"
            echo "  nix run .#unseed  - Remove all user and seed data"
            echo "======================================================="
          '';
        };
      }
    );
}