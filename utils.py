import os
import glob
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class VersaoAnterior:
    def __init__(self, backup_dir="backup_logs", agent_file_path="agente_hifen.py"):
        self.backup_dir = backup_dir
        self.agent_file_path = agent_file_path
        os.makedirs(self.backup_dir, exist_ok=True)

    def criar_backup(self, codigo: str) -> str | None:
        """Cria backup do código fornecido com timestamp."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Garante que o nome do arquivo de backup seja baseado no nome do arquivo original
            base_agent_file_name = os.path.basename(self.agent_file_path)
            backup_filename = f"backup_{timestamp}_{base_agent_file_name}"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(codigo)
            logger.info(f"Backup criado: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            return None

    def restaurar_backup_recente(self) -> bool:
        """Restaura o backup mais recente do arquivo do agente."""
        try:
            # Busca backups especificamente do agent_file_path
            search_pattern = os.path.join(self.backup_dir, f"backup_*_{os.path.basename(self.agent_file_path)}")
            backups = sorted(glob.glob(search_pattern), key=os.path.getmtime, reverse=True)

            if not backups:
                logger.warning(f"Nenhum backup encontrado para {self.agent_file_path} em {self.backup_dir}")
                return False

            backup_recente = backups[0]

            with open(backup_recente, 'r', encoding='utf-8') as f:
                codigo_backup = f.read()

            with open(self.agent_file_path, 'w', encoding='utf-8') as f:
                f.write(codigo_backup)

            logger.critical(f"RESTAURADO BACKUP: {backup_recente} para {self.agent_file_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}")
            return False

    def ler_historico_de_backups(self) -> list:
        """Lê o histórico de backups para o arquivo do agente."""
        try:
            search_pattern = os.path.join(self.backup_dir, f"backup_*_{os.path.basename(self.agent_file_path)}")
            backup_files = sorted(glob.glob(search_pattern), key=os.path.getmtime, reverse=True)

            historico = []
            for backup_file_path in backup_files:
                try:
                    with open(backup_file_path, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                        historico.append({
                            'arquivo': backup_file_path,
                            'conteudo': conteudo,
                            # Adicionar hash pode ser útil, mas requer hashlib
                            # 'hash': hashlib.md5(conteudo.encode()).hexdigest()
                        })
                except Exception as e_file:
                    logger.error(f"Erro ao ler arquivo de backup {backup_file_path}: {e_file}")
            return historico
        except Exception as e:
            logger.error(f"Erro ao ler histórico de backups: {e}")
            return []

if __name__ == '__main__':
    # Exemplo de uso (para teste)
    logging.basicConfig(level=logging.INFO)

    # CUIDADO: Este teste irá modificar agente_hifen.py se ele existir no diretório atual.
    # Crie um agente_hifen.py de teste ou ajuste o agent_file_path.
    test_agent_file = "agente_hifen_teste.py"
    with open(test_agent_file, "w") as f:
        f.write("# Código inicial de teste\nprint('Versão 0')")

    gestor_versao = VersaoAnterior(agent_file_path=test_agent_file)

    # Criar um backup
    with open(test_agent_file, "r") as f:
        current_code = f.read()
    gestor_versao.criar_backup(current_code)

    # Modificar o arquivo
    with open(test_agent_file, "w") as f:
        f.write("# Código modificado\nprint('Versão 1')")
    logger.info(f"Conteúdo de {test_agent_file} após modificação: ")
    with open(test_agent_file, "r") as f:
        logger.info(f.read())

    # Restaurar backup
    if gestor_versao.restaurar_backup_recente():
        logger.info(f"Conteúdo de {test_agent_file} após restauração: ")
        with open(test_agent_file, "r") as f:
            logger.info(f.read())

    # Ler histórico
    historico = gestor_versao.ler_historico_de_backups()
    logger.info(f"Histórico de backups ({len(historico)} versões):")
    for i, versao in enumerate(historico):
        logger.info(f"  {i+1}. {versao['arquivo']}")

    # Limpeza (opcional)
    # os.remove(test_agent_file)
    # for backup_file in glob.glob(os.path.join(gestor_versao.backup_dir, f"backup_*_{os.path.basename(test_agent_file)}")):
    #     os.remove(backup_file)
    # if not os.listdir(gestor_versao.backup_dir):
    #     os.rmdir(gestor_versao.backup_dir)
    pass
