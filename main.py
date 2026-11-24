
import argparse

from app import Aplicacao


def main() -> None:
    parser = argparse.ArgumentParser(description="Editor de imagens e vídeo com OpenCV")
    parser.add_argument("foto", nargs="?", help="foto para abrir ao iniciar (opcional)")
    args = parser.parse_args()
    Aplicacao().executar(args.foto)


if __name__ == "__main__":
    main()