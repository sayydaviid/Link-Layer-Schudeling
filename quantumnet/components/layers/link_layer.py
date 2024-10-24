import networkx as nx
from quantumnet.components import Host
from quantumnet.objects import Logger, Epr
from random import uniform
import random

class LinkLayer:
    def __init__(self, network, physical_layer):
        """
        Inicializa a camada de enlace.
        
        Args:
            network : Network : Rede.
            physical_layer : PhysicalLayer : Camada física.
        """
        self._network = network
        self._physical_layer = physical_layer
        self._requests = []
        self._failed_requests = []
        self.logger = Logger.get_instance()
        self.used_eprs = 0  # Inicializa o contador de EPRs utilizados
        self.used_qubits = 0  # Inicializa o contador de Qubits utilizados
        self.created_eprs = []  # Armazenar os EPRs criados pela camada física

    @property
    def requests(self):
        return self._requests

    @property
    def failed_requests(self):
        return self._failed_requests

    def __str__(self):
        """ Retorna a representação em string da camada de enlace. 
        
        Returns:
            str : Representação em string da camada de enlace.
        """
        return 'Link Layer'
    
    def get_used_eprs(self):
        self.logger.debug(f"Eprs usados na camada {self.__class__.__name__}: {self.used_eprs}")
        return self.used_eprs
    
    def get_used_qubits(self):
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits
    
    def request(self, alice_id: int, bob_id: int):
        """
        Solicitação de criação de emaranhamento entre Alice e Bob.
        
        Args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
        """
        try:
            alice = self._network.get_host(alice_id)
            bob = self._network.get_host(bob_id)
        except KeyError:
            self.logger.log(f'Host {alice_id} ou {bob_id} não encontrado na rede.')
            return False

        for attempt in range(1, 3):
            self._network.timeslot()
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: Tentativa de emaranhamento entre {alice_id} e {bob_id}.')

            entangle = self._physical_layer.entanglement_creation_heralding_protocol(alice, bob)

            # Após cada tentativa de emaranhamento, transferimos os EPRs criados para a camada de enlace
            if entangle:
                self.used_eprs += 1
                self.used_qubits += 2
                self._requests.append((alice_id, bob_id))

                # Adiciona os EPRs criados pela camada física à lista de EPRs criados da camada de enlace
                if self._physical_layer.created_eprs:
                    self.created_eprs.extend(self._physical_layer.created_eprs)
                    self._physical_layer.created_eprs.clear()  # Limpa a lista da camada física
                
                self.logger.log(f'Timeslot {self._network.get_timeslot()}: Entrelaçamento criado entre {alice} e {bob} na tentativa {attempt}.')
                return True
            else:
                self.logger.log(f'Timeslot {self._network.get_timeslot()}: Entrelaçamento falhou entre {alice} e {bob} na tentativa {attempt}.')
                self._failed_requests.append((alice_id, bob_id))

        # Verifica se deve realizar a purificação após duas falhas
        if len(self._failed_requests) >= 2:
            purification_success = self.purification(alice_id, bob_id)
            
            # Independente de a purificação ser bem-sucedida ou não, sempre transferimos os EPRs criados
            if self._physical_layer.created_eprs:
                self.created_eprs.extend(self._physical_layer.created_eprs)
                self._physical_layer.created_eprs.clear()  # Limpa a lista da camada física
            
            return purification_success

        # Após a segunda tentativa, garante que todos os EPRs criados sejam transferidos
        if self._physical_layer.created_eprs:
            self.created_eprs.extend(self._physical_layer.created_eprs)
            self._physical_layer.created_eprs.clear()  # Limpa a lista da camada física
            
        return False

    def purification_calculator(self, f1: int, f2: int, purification_type: int) -> float:
        """
        Cálculo das fórmulas de purificação.
        
        Args:
            f1: int : Fidelidade do primeiro EPR.
            f2: int : Fidelidade do segundo EPR.
            purification_type: int : Fórmula escolhida (1 - Default, 2 - BBPSSW Protocol, 3 - DEJMPS Protocol).
        
        Returns:
            float : Fidelidade após purificação.
        """
        f1f2 = f1 * f2

        if purification_type == 1:
            self.logger.log('A purificação utilizada foi tipo 1.')
            return f1f2 / ((f1f2) + ((1 - f1) * (1 - f2)))

        elif purification_type == 2:
            result = (f1f2 + ((1 - f1) / 3) * ((1 - f2) / 3)) / (f1f2 + f1 * ((1 - f2) / 3) + f2 * ((1 - f1) / 3) + 5 * ((1 - f1) / 3) * ((1 - f2) / 3))
            self.logger.log('A purificação utilizada foi tipo 2.')
            return result

        elif purification_type == 3:
            result = (2 * f1f2 + 1 - f1 - f2) / ((1 / 4) * (f1 + f2 - f1f2) + 3 / 4)
            self.logger.log('A purificação utilizada foi tipo 3.')
            return result
        
        self.logger.log('Purificação só pode aceitar os valores (1, 2 ou 3), a fórmula 1 foi escolhida por padrão.')
        return f1f2 / ((f1f2) + ((1 - f1) * (1 - f2)))


    def purification(self, alice_id: int, bob_id: int, purification_type: int = 1):
        """
        Purificação de EPRs.

        Args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
            purification_type : int : Tipo de protocolo de purificação.
        """
        self._network.timeslot()  # Incrementa o timeslot para a tentativa de purificação

        eprs_fail = self._physical_layer.failed_eprs

        if len(eprs_fail) < 2:
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: Não há EPRs suficientes para purificação no canal ({alice_id}, {bob_id}).')
            return False

        eprs_fail1 = eprs_fail[-1]
        eprs_fail2 = eprs_fail[-2]
        f1 = eprs_fail1.get_current_fidelity()
        f2 = eprs_fail2.get_current_fidelity()

        purification_prob = (f1 * f2) + ((1 - f1) * (1 - f2))

        # Incrementa a contagem de EPRs utilizados, pois ambos serão usados na tentativa de purificação
        self.used_eprs += 2
        self.used_qubits += 4

        if purification_prob > 0.5:
            new_fidelity = self.purification_calculator(f1, f2, purification_type)

            if new_fidelity > 0.8:  # Verifica se a nova fidelidade é maior que 0.8
                epr_purified = Epr((alice_id, bob_id), new_fidelity)
                self._physical_layer.add_epr_to_channel(epr_purified, (alice_id, bob_id))
                self._physical_layer.failed_eprs.remove(eprs_fail1)
                self._physical_layer.failed_eprs.remove(eprs_fail2)
                self.logger.log(f'EPRS Usados {self.used_eprs}')
                self.logger.log(f'Timeslot {self._network.get_timeslot()}: Purificação bem sucedida no canal ({alice_id}, {bob_id}) com nova fidelidade {new_fidelity}.')
                return True
            else:
                self._physical_layer.failed_eprs.remove(eprs_fail1)
                self._physical_layer.failed_eprs.remove(eprs_fail2)
                self.logger.log(f'Timeslot {self._network.get_timeslot()}: Purificação falhou no canal ({alice_id}, {bob_id}) devido a baixa fidelidade após purificação.')
                return False
        else:
            self._physical_layer.failed_eprs.remove(eprs_fail1)
            self._physical_layer.failed_eprs.remove(eprs_fail2)
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: Purificação falhou no canal ({alice_id}, {bob_id}) devido a baixa probabilidade de sucesso da purificação.')
            return False

    def avg_fidelity_on_linklayer(self):
        """
        Calcula a fidelidade média dos EPRs criados na camada de enlace.
        
        Returns:
            float : Fidelidade média dos EPRs da camada de enlace.
        """
        total_fidelity = 0
        total_eprs = len(self.created_eprs)

        for epr in self.created_eprs:   
            total_fidelity += epr.get_current_fidelity()

        if total_eprs == 0:
            self.logger.log('Não há EPRs criados na camada de enlace.')
            return 0


        print(f'Total de EPRs criados na camada de enlace: {total_eprs}')
        print(f'Total de fidelidade dos EPRs criados na camada de enlace: {total_fidelity}')
        avg_fidelity = total_fidelity / total_eprs
        self.logger.log(f'A fidelidade média dos EPRs criados na camada de enlace é {avg_fidelity}')
        return avg_fidelity


    
    def purification_scheduling(self, alice_id: int, bob_id: int, purification_type: str, rounds: int = 1):
        """
        Função de agendamento de purificação, que executa tanto a purificação symétrica quanto a pumping.

        Args:
            alice_id (int): ID do host Alice.
            bob_id (int): ID do host Bob.
            purification_type (str): Tipo de purificação a ser realizada ('symmetric' ou 'pumping').
            rounds (int): Número de rounds de purificação. Aplica-se apenas para purificação symétrica.
        
        Returns:
            bool: True se a purificação foi bem-sucedida, False caso contrário.
        """
        # Obtém os EPRs do canal entre Alice e Bob
        eprs = self._network.get_eprs_from_edge(alice_id, bob_id)

        if len(eprs) < 2:
            self.logger.log(f"Não há EPRs suficientes para realizar a purificação. São necessários pelo menos 2 EPRs.")
            return False

        # Seleciona os dois últimos pares EPRs criados
        epr1 = eprs[-2]
        epr2 = eprs[-1]
        # Obtém as fidelidades dos dois últimos EPRs
        f1 = epr1.get_current_fidelity()
        f2 = epr2.get_current_fidelity()

        if purification_type == 'symmetric':
            # Realiza a purificação simétrica para múltiplos rounds
            return self.purification_symmetric(alice_id, bob_id, rounds)

        elif purification_type == 'pumping':
            # Realiza a purificação por bombardeamento
            return self.purification_pumping(alice_id, bob_id, f1, f2, rounds)

        else:
            self.logger.log("Tipo de purificação inválido. Escolha 'symmetric' ou 'pumping'.")
            return False


    def scheduling_verify(self, alice_id: int, bob_id: int, rounds: int) -> bool:
        """
        Verifica se há a quantidade de EPRs necessários para a purificação e cria mais se necessário.

        Args:
            alice_id (int): ID do host Alice.
            bob_id (int): ID do host Bob.
            rounds (int): Número de rounds de purificação.

        Returns:
            bool: True se houver EPRs suficientes após a verificação, False caso contrário.
        """
        # Calcula o número necessário de EPRs baseado no número de rounds
        required_eprs = 2 ** rounds
        eprs = self._network.get_eprs_from_edge(alice_id, bob_id)
        available_eprs = len(eprs)
        
        # Verifica se a quantidade disponível é suficiente
        if available_eprs < required_eprs:
            missing_eprs = required_eprs - available_eprs
            self.logger.log(f"Não há EPRs suficientes para purificação. Necessário: {required_eprs}, Disponível: {available_eprs}. Criando {missing_eprs} EPRs adicionais.")
            
            # Cria os EPRs necessários e evita duplicação
            for _ in range(missing_eprs):
                new_epr = self._physical_layer.create_epr_pair(alice_id, bob_id)
                self._physical_layer.add_epr_to_channel(new_epr, (alice_id, bob_id))

            self.logger.log(f"Total de {missing_eprs} EPRs criados e adicionados ao canal entre {alice_id} e {bob_id}.")
            
            # Atualiza a lista de EPRs com os novos EPRs criados
            eprs = self._network.get_eprs_from_edge(alice_id, bob_id)
            self.used_eprs = len(eprs)  # Atualiza o contador de EPRs utilizados
            
        # Verificação final se os EPRs são suficientes
        if len(eprs) >= required_eprs:
            self.logger.log(f"Agora há EPRs suficientes para a purificação: {len(eprs)} disponíveis.")
            return True
        else:
            self.logger.log(f"Ainda não há EPRs suficientes após a criação. Disponíveis: {len(eprs)}, Necessários: {required_eprs}.")
            return False
        
    def purification_symmetric(self, alice_id: int, bob_id: int, rounds: int) -> bool:
        """
        Purificação Simétrica de EPRs.

        Args:
            alice_id (int): ID do host Alice.
            bob_id (int): ID do host Bob.
            rounds (int): Número de rounds de purificação.

        Returns:
            bool: True se a purificação foi bem-sucedida, False caso contrário.
        """

        self.logger.log(f"Iniciando purificação simétrica entre {alice_id} e {bob_id} para {rounds} rounds.")
        
        # Verifica e garante que há EPRs suficientes
        if not self.scheduling_verify(alice_id, bob_id, rounds):
            self.logger.log(f"Falha na verificação dos EPRs. Purificação abortada.")
            return False

        # Executa a purificação por rounds
        for round_num in range(rounds):
            self.logger.log(f"Executando round {round_num + 1} de purificação simétrica.")
            
            # Pega todos os EPRs atuais entre Alice e Bob
            eprs = self._network.get_eprs_from_edge(alice_id, bob_id)
            
            # Determina o número necessário de EPRs para o round atual
            num_eprs_necessarios = 2 ** (rounds - round_num)  # Exemplo: 4 EPRs no primeiro round, 2 no segundo

            if len(eprs) < num_eprs_necessarios:
                self.logger.log(f"Não há EPRs suficientes para purificação no round {round_num + 1}. Abortando.")
                return False
            
            new_eprs = []  # Lista para armazenar os novos EPRs após purificação
            
            # Aplica purificação em pares de EPRs
            for i in range(0, num_eprs_necessarios, 2):  # Itera de 2 em 2
                epr1 = eprs[i]
                epr2 = eprs[i + 1]
                
                f1 = epr1.get_current_fidelity()
                f2 = epr2.get_current_fidelity()
                self.logger.log(f"Purificando par de EPRs: fidelidades {f1} e {f2}.")
                
                # Pega as informações do canal
                channel_info = self._network.get_channel_info(alice_id, bob_id)
                canal_tipo = channel_info.get('type', 'desconhecido')

                # Determina a probabilidade de sucesso e a nova fidelidade com base no tipo de canal
                if canal_tipo in ['X', 'Z','Y' ]:
                    p_success = f1 * f2 + (1 - f1) * (1 - f2)
                    x = random.uniform(0, 1)
                    self.logger.log(f"o valor de x é: {x}")
                    if p_success >= x:
                        new_fidelity = f1 * f2 / (f1 * f2 + (1-f1) * (1-f2))
                        self.logger.log(f"Round {round_num + 1} - Probabilidade de sucesso: {p_success} (Erro X ou XZ) - Fidelidade: {new_fidelity}")
                    else:
                        self.logger.log(f"Round {round_num + 1} - Purificação falhou devido à baixa probabilidade de sucesso: {p_success}.")
                        return False
                elif canal_tipo == 'XZ':
                # Estado de Werner
                    p_success = ((f1 + (1 - f1) / 3) * (f2 + (1 - f2) / 3) +
                                (2 * (1 - f1) / 3) * (2 * (1 - f2) / 3))
                    x = random.uniform(0, 1)
                    self.logger.log(f"o valor de x é: {x}")
                    if p_success >= x:
                        new_fidelity = (f1 * f2 + ((1 - f1) * (1 - f2)) / 3**2) / p_success
                        self.logger.log(f"Round {round_num + 1} - Probabilidade de sucesso: {p_success} (Estado de Werner) - Fidelidade: {new_fidelity}")
                    else:
                        self.logger.log(f"Round {round_num + 1} - Purificação falhou devido à baixa probabilidade de sucesso: {p_success}.")
                        return False
                    
                    
                else:
                    self.logger.log(f"Tipo de canal '{canal_tipo}' não identificado para a purificação.")
                    return False


                    
                # Criação de um novo par EPR com fidelidade pós-purificação
                epr_purified = self._physical_layer.create_epr_pair(fidelity=new_fidelity)
                new_eprs.append(epr_purified)

            # Remove os EPRs antigos usados no round atual do canal
            try:
                self._physical_layer.remove_epr_from_channel(eprs[:num_eprs_necessarios], (alice_id, bob_id))
            except ValueError as e:
                self.logger.log(f"Erro ao remover EPRs do canal: {e}. Tentando continuar.")

            # Adiciona os novos EPRs purificados ao canal
            for epr_purified in new_eprs:
                self._physical_layer.add_epr_to_channel(epr_purified, (alice_id, bob_id))

            self.logger.log(f"Round {round_num + 1} de purificação concluído com sucesso.")

        # Certifica-se de que o número de EPRs após o último round é 1
        self.logger.log(f"Purificação simétrica entre {alice_id} e {bob_id} concluída com sucesso.")
        return True


    def purification_pumping(self, alice_id: int, bob_id: int, rounds: int) -> bool:
        """
        Purificação por Bombardeamento (Pumping) de EPRs com verificação de canal e criação conforme necessário.

        Args:
            alice_id (int): ID do host Alice.
            bob_id (int): ID do host Bob.
            rounds (int): Número de rounds de purificação.

        Returns:
            bool: True se a purificação foi bem-sucedida, False caso contrário.
        """
        
        self.logger.log(f"Iniciando purificação por bombardeamento entre {alice_id} e {bob_id} para {rounds} rounds.")
        
        eprs = self._network.get_eprs_from_edge(alice_id, bob_id)
        new_epr = None
        
        for round_num in range(rounds):
            if len(eprs) < 2:
                # Se não houver EPRs suficientes, cria novos
                missing_eprs = 2 - len(eprs)
                self.logger.log(f"Faltam {missing_eprs} EPRs para o round {round_num + 1}. Criando mais EPRs...")
                for _ in range(missing_eprs):
                    new_base_epr = self._physical_layer.create_epr_pair(alice_id, bob_id)
                    self._physical_layer.add_epr_to_channel(new_base_epr, (alice_id, bob_id))
                    eprs.append(new_base_epr)

            if round_num == 0:
                # No primeiro round, pega dois EPRs do canal e cria um novo (f')
                epr1 = eprs[-2]
                epr2 = eprs[-1]
                self.logger.log(f"Round {round_num + 1}: Pegando dois EPRs base para purificação: f_base1 (fidelidade {epr1.get_current_fidelity()}) e f_base2 (fidelidade {epr2.get_current_fidelity()}).")
            elif round_num == 1:
                # No segundo round, pega o EPR purificado (f') e outro EPR base do canal
                epr1 = new_epr  # f'
                epr2 = eprs[-2]  # f_base
                self.logger.log(f"Round {round_num + 1}: Pegando EPR purificado f' (fidelidade {epr1.get_current_fidelity()}) e EPR base ( fidelidade {epr2.get_current_fidelity()}).")
            else:
                # Nos rounds subsequentes, pega o EPR purificado (f'') e outro EPR base do canal
                epr1 = new_epr  # f''
                epr2 = eprs[-2]  # f_base
                self.logger.log(f"Round {round_num + 1}: Pegando EPR purificado f'' (fidelidade {epr1.get_current_fidelity()}) e EPR base ( fidelidade {epr2.get_current_fidelity()}).")

            # Fidelidades dos dois EPRs
            f1 = epr1.get_current_fidelity()
            f2 = epr2.get_current_fidelity()
            self.logger.log(f"Purificando par de EPRs: fidelidades {f1} e {f2}.")
            
            # Verifica o tipo de canal
            channel_info = self._network.get_channel_info(alice_id, bob_id)
            canal_tipo = channel_info.get('type', 'desconhecido')

            # Determina a probabilidade de sucesso e a nova fidelidade com base no tipo de canal
            if canal_tipo in ['X', 'Z', 'Y']:
                p_success = f1 * f2 + (1 - f1) * (1 - f2)
                x = random.uniform(0, 1)
                
                if p_success >= x:
                    new_fidelity = f1 * f2 / (f1 * f2 + (1 - f1) * (1 - f2))
                    self.logger.log(f"Round {round_num + 1} - Probabilidade de sucesso: {p_success} (Erro X, Z ou Y)")
                else:
                    self.logger.log(f"Round {round_num + 1} - Purificação falhou devido à baixa probabilidade de sucesso: {p_success}.")
                    return False
            
            elif canal_tipo == 'XZ':
                # Estado de Werner
                p_success = ((f1 + (1 - f1) / 3) * (f2 + (1 - f2) / 3) +
                            (2 * (1 - f1) / 3) * (2 * (1 - f2) / 3))
                x = random.uniform(0, 1)
                
                if p_success >= x:
                    new_fidelity = (f1 * f2 + ((1 - f1) * (1 - f2)) / 3**2) / p_success
                    self.logger.log(f"Round {round_num + 1} - Probabilidade de sucesso: {p_success} (Estado de Werner) - Fidelidade: {new_fidelity}")
                else:
                    self.logger.log(f"Round {round_num + 1} - Purificação falhou devido à baixa probabilidade de sucesso: {p_success}.")
                    return False
            
            else:
                self.logger.log(f"Tipo de canal '{canal_tipo}' não identificado para a purificação.")
                return False

            # Criação de um novo par EPR com fidelidade pós-purificação
            new_epr = self._physical_layer.create_epr_pair(fidelity=new_fidelity)

            # Remover EPRs antigos usados no round atual do canal
            if round_num == 0:
                self.logger.log(f"Removendo EPRs usados no round {round_num + 1}: f_base1 e f_base2.")
            elif round_num == 1:
                self.logger.log(f"Removendo EPRs usados no round {round_num + 1}: f' e f_base.")
            else:
                self.logger.log(f"Removendo EPRs usados no round {round_num + 1}: f'' e f_base.")

            self._physical_layer.remove_epr_from_channel([epr1, epr2], (alice_id, bob_id))

            # Adicionar novo EPR purificado ao canal
            self.logger.log(f"Adicionando novo EPR purificado ao canal no round {round_num + 1}, com fidelidade {new_epr.get_current_fidelity()}.")
            self._physical_layer.add_epr_to_channel(new_epr, (alice_id, bob_id))

            self.logger.log(f"Round {round_num + 1} de purificação por bombardeamento concluído com sucesso.")

            # Verifica se há EPRs suficientes para o próximo round e cria se necessário
            eprs = self._network.get_eprs_from_edge(alice_id, bob_id)
        
        self.logger.log(f"Purificação por bombardeamento concluída com sucesso entre {alice_id} e {bob_id}.")
        return True




# def purification_pumping(self, alice_id: int, bob_id: int, rounds: int) -> bool:
#         """
#         Purificação por Bombardeamento (Pumping) de EPRs com verificação de canal e agendamento.

#         Args:
#             alice_id (int): ID do host Alice.
#             bob_id (int): ID do host Bob.
#             rounds (int): Número de rounds de purificação.

#         Returns:
#             bool: True se a purificação foi bem-sucedida, False caso contrário.
#         """
        
#         self.logger.log(f"Iniciando purificação por bombardeamento entre {alice_id} e {bob_id} para {rounds} rounds.")
        
#         # Verifica e agenda criação de EPRs necessários antes de iniciar a purificação
#         if not self.schedulinng_verify(alice_id, bob_id, rounds):
#             self.logger.log(f"Falha na verificação dos EPRs. Purificação abortada.")
#             return False
        
#         eprs = self._network.get_eprs_from_edge(alice_id, bob_id)
#         new_epr = None
        
#         for round_num in range(rounds):
#             if round_num == 0:
#                 # No primeiro round, pega dois EPRs do canal e cria um novo (f')
#                 epr1 = eprs[-2]
#                 epr2 = eprs[-1]
#                 self.logger.log(f"Round {round_num + 1}: Pegando dois EPRs base para purificação: f_base1 (fidelidade {epr1.get_current_fidelity()}) e f_base2 (fidelidade {epr2.get_current_fidelity()}).")
#             elif round_num == 1:
#                 # No segundo round, pega o EPR purificado (f') e outro EPR base do canal
#                 epr1 = new_epr  # f'
#                 epr2 = eprs[-1]  # f_base
#                 self.logger.log(f"Round {round_num + 1}: Pegando EPR purificado f' (fidelidade {epr1.get_current_fidelity()}) e EPR base (f_base, fidelidade {epr2.get_current_fidelity()}).")
#             else:
#                 # Nos rounds subsequentes, pega o EPR purificado (f'') e outro EPR base do canal
#                 epr1 = new_epr  # f''
#                 epr2 = eprs[-1]  # f_base
#                 self.logger.log(f"Round {round_num + 1}: Pegando EPR purificado f'' (fidelidade {epr1.get_current_fidelity()}) e EPR base (f_base, fidelidade {epr2.get_current_fidelity()}).")

#             # Fidelidades dos dois EPRs
#             f1 = epr1.get_current_fidelity()
#             f2 = epr2.get_current_fidelity()
#             self.logger.log(f"Purificando par de EPRs: fidelidades {f1} e {f2}.")
            
#             # Verifica o tipo de canal
#             channel_info = self._network.get_channel_info(alice_id, bob_id)
#             canal_tipo = channel_info.get('type', 'desconhecido')

#             # Determina a probabilidade de sucesso e a nova fidelidade com base no tipo de canal
#             if canal_tipo in ['X', 'Z', 'Y']:
#                 p_success = f1 * f2 + (1 - f1) * (1 - f2)
#                 x = random.uniform(0, 1)
                
#                 if p_success >= x:
#                     new_fidelity = f1 * f2 / (f1 * f2 + (1 - f1) * (1 - f2))
#                     self.logger.log(f"Round {round_num + 1} - Probabilidade de sucesso: {p_success} (Erro X, Z ou Y) - Fidelidade: {new_fidelity}")
#                 else:
#                     self.logger.log(f"Round {round_num + 1} - Purificação falhou devido à baixa probabilidade de sucesso: {p_success}.")
#                     return False
            
#             elif canal_tipo == 'XZ':
#                 # Estado de Werner
#                 p_success = ((f1 + (1 - f1) / 3) * (f2 + (1 - f2) / 3) +
#                             (2 * (1 - f1) / 3) * (2 * (1 - f2) / 3))
#                 x = random.uniform(0, 1)
                
#                 if p_success >= x:
#                     new_fidelity = (f1 * f2 + ((1 - f1) * (1 - f2)) / 3**2) / p_success
#                     self.logger.log(f"Round {round_num + 1} - Probabilidade de sucesso: {p_success} (Estado de Werner) - Fidelidade: {new_fidelity}")
#                 else:
#                     self.logger.log(f"Round {round_num + 1} - Purificação falhou devido à baixa probabilidade de sucesso: {p_success}.")
#                     return False
            
#             else:
#                 self.logger.log(f"Tipo de canal '{canal_tipo}' não identificado para a purificação.")
#                 return False

#             # Criação de um novo par EPR com fidelidade pós-purificação
#             new_epr = self._physical_layer.create_epr_pair(fidelity=new_fidelity)

#             # Remover EPRs antigos usados no round atual do canal
#             if round_num == 0:
#                 self.logger.log(f"Removendo EPRs usados no round {round_num + 1}: f_base1 e f_base2.")
#             elif round_num == 1:
#                 self.logger.log(f"Removendo EPRs usados no round {round_num + 1}: f' e f_base.")
#             else:
#                 self.logger.log(f"Removendo EPRs usados no round {round_num + 1}: f'' e f_base.")

#             self._physical_layer.remove_epr_from_channel([epr1, epr2], (alice_id, bob_id))

#             # Adicionar novo EPR purificado ao canal
#             self.logger.log(f"Adicionando novo EPR purificado ao canal no round {round_num + 1}, com fidelidade {new_epr.get_current_fidelity()}.")
#             self._physical_layer.add_epr_to_channel(new_epr, (alice_id, bob_id))

#             self.logger.log(f"Round {round_num + 1} de purificação por bombardeamento concluído com sucesso.")

#         self.logger.log(f"Purificação por bombardeamento concluída com sucesso entre {alice_id} e {bob_id}.")
#         return True



