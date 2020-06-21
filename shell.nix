with import <nixpkgs> {};

mkShell {
  buildInputs = [
    python38
    python3Packages.pyzmq
    python38Packages.setuptools
    python38Packages.pip
  ];
  shellHook = ''
    alias pip="PIP_PREFIX='$(pwd)/_build/pip_packages' \pip"
    export PYTHONPATH="$(pwd)/_build/pip_packages/lib/python3.8/site-packages:$PYTHONPATH"
    # export PYTHONPATH="$PYTHONPATH:$(pwd)"
    unset SOURCE_DATE_EPOCH
    # pip install pathlib
    # pip install aiogram
    pip install -e .
  '';
}
