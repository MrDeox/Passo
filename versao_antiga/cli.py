import argparse
import sys
import logging
import empresa_digital as ed # Assuming empresa_digital.py is in the same package or PYTHONPATH

# Configure logging at the CLI entry point
# This basic configuration can be expanded or moved if a more complex logging setup is needed.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Simulador de Empresa Digital Autônoma")
    parser.add_argument(
        "--cycles", "-c", type=int, default=0,
        help="Número de ciclos para executar. 0 ou negativo para execução infinita (padrão: 0)."
    )
    parser.add_argument(
        "--resume", "-r", action="store_true",
        help="Retomar a simulação do estado salvo."
    )
    # Example: Add other arguments if needed in the future
    # parser.add_argument(
    #     "--config-file", type=str, help="Caminho para o arquivo de configuração da simulação."
    # )

    args = parser.parse_args()

    try:
        # Pass arguments to the main simulation entry point function in empresa_digital.py
        ed.run_simulation_entry_point(num_cycles=args.cycles, resume_flag=args.resume)
    except KeyboardInterrupt:
        # This top-level KeyboardInterrupt is a fallback if the one in run_simulation_entry_point doesn't catch it first
        # or if the interrupt happens outside the main loop managed there.
        logging.info("Simulação interrompida externamente (Ctrl-C).")
        # Consider if saving is needed here; run_simulation_entry_point should handle its own saving.
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Erro fatal não tratado na execução da simulação: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
