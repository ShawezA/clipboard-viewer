let
  pkgs = import <nixpkgs> {};
in
pkgs.python3Packages.buildPythonApplication rec {
  pname = "catppuccin-clipboard-preview";
  version = "0.1.0"; # Should match setup.py

  src = ./.;

  propagatedBuildInputs = [
    pkgs.python3Packages.pygobject3
    pkgs.python3Packages.setuptools
  ];

  nativeBuildInputs = [
    pkgs.wrapGAppsHook # Hook to wrap GTK applications
    pkgs.gobject-introspection
    pkgs.pkg-config
    pkgs.coreutils # For a known-good `install` in postFixup
  ];

  buildInputs = [
    pkgs.gtk3
    pkgs.gdk-pixbuf
    pkgs.pango
    pkgs.cliphist
    pkgs.wl-clipboard
    pkgs.socat
    pkgs.nerdfonts
  ];

  doCheck = false;

  installPhase = ''
    runHook preInstall

    # setup.py installs clipboard_preview.py to $out/bin
    python setup.py install --prefix=$out --skip-build

    # Manually install the show-clipboard-preview.sh script to $out/bin
    # This version will likely get wrapped and renamed.
    install -Dm755 ${src}/show-clipboard-preview.sh $out/bin/show-clipboard-preview

    runHook postInstall
  '';

  # We still hope gappsTargets helps direct wrapGAppsHook primarily to the python script,
  # reducing unintended side effects, though it seems to wrap all executables anyway.
  gappsTargets = [ "bin/clipboard_preview.py" ];

  postFixup = ''
    # After all other fixup hooks (like wrapGAppsHook) have run,
    # forcefully re-install the correct show-clipboard-preview.sh script.
    # This will overwrite any C wrapper that was incorrectly created for it.
    echo "Running postFixup: Re-installing show-clipboard-preview.sh"
    install -Dm755 ${src}/show-clipboard-preview.sh $out/bin/show-clipboard-preview
    echo "Listing $out/bin after postFixup re-install:"
    ls -la $out/bin
  '';

  meta = with pkgs.lib; {
    description = "A GTK clipboard history previewer with Catppuccin theme, using cliphist.";
    homepage = "";
    license = licenses.mit;
    maintainers = with maintainers; [ ];
    mainProgram = "show-clipboard-preview";
    platforms = platforms.linux;
  };
}