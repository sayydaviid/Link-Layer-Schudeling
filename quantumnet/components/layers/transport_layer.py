import networkx as nx
from quantumnet.components import Host
from quantumnet.objects import Logger, Epr
from random import uniform

class TransportLayer:
    def __init__(self, network, network_layer, link_layer, physical_layer):
        """
        Inicializa a camada de transporte.
        
        args:
            network : Network : Rede.
            network_layer : NetworkLayer : Camada de rede.
            link_layer : LinkLayer : Camada de enlace.
            physical_layer : PhysicalLayer : Camada física.
        """
        self._network = network
        self._physical_layer = physical_layer
        self._network_layer = network_layer
        self._link_layer = link_layer
        self.logger = Logger.get_instance()
        self.transmitted_qubits = []
        self.used_eprs = 0
        self.used_qubits = 0
        self.created_eprs = []  # Lista para armazenar EPRs criados

    def __str__(self):
        """ Retorna a representação em string da camada de transporte. 
        
        returns:
            str : Representação em string da camada de transporte."""
        return f'Transport Layer'
    
    def get_used_eprs(self):
        self.logger.debug(f"Eprs usados na camada {self.__class__.__name__}: {self.used_eprs}")
        return self.used_eprs
    
    def get_used_qubits(self):
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits
    
    def request_transmission(self, alice_id: int, bob_id: int, num_qubits: int):
        """
        Requisição de transmissão de n qubits entre Alice e Bob.
        
        args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
            num_qubits : int : Número de qubits a serem transmitidos.
            
        returns:
            bool : True se a transmissão foi bem-sucedida, False caso contrário.
        """
        alice = self._network.get_host(alice_id)
        available_qubits = len(alice.memory)

        if available_qubits < num_qubits:
            self.logger.log(f'Número insuficiente de qubits na memória de Alice (Host:{alice_id}). Tentando transmitir os {available_qubits} qubits disponíveis.')
            num_qubits = available_qubits

        if num_qubits == 0:
            self.logger.log(f'Nenhum qubit disponível na memória de Alice ({alice_id}) para transmissão.')
            return False

        max_attempts = 2
        attempts = 0
        success = False

        while attempts < max_attempts and not success:
            self._network.timeslot()  # Incrementa o timeslot para cada tentativa de transmissão
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: Tentativa de transmissão {attempts + 1} entre {alice_id} e {bob_id}.')
            
            routes = []
            for _ in range(num_qubits):
                route = self._network_layer.short_route_valid(alice_id, bob_id)
                if route is None:
                    self.logger.log(f'Não foi possível encontrar uma rota válida na tentativa {attempts + 1}. Timeslot: {self._network.get_timeslot()}')
                    break
                routes.append(route)
            
            if len(routes) == num_qubits:
                success = True
                for route in routes:
                    for i in range(len(route) - 1):
                        node1 = route[i]
                        node2 = route[i + 1]
                        # Verifica se há pelo menos um par EPR disponível no canal
                        if len(self._network.get_eprs_from_edge(node1, node2)) < 1:
                            self.logger.log(f'Falha ao encontrar par EPR entre {node1} e {node2} na tentativa {attempts + 1}. Timeslot: {self._network.get_timeslot()}')
                            success = False
                            break
                    if not success:
                        break
            
            if not success:
                attempts += 1

        if success:
            # Registrar os qubits transmitidos
            for route in routes:
                qubit_info = {
                    'route': route,
                    'alice_id': alice_id,
                    'bob_id': bob_id,
                }
                self.transmitted_qubits.append(qubit_info)
            self.logger.log(f'Transmissão de {num_qubits} qubits entre {alice_id} e {bob_id} concluída com sucesso. Timeslot: {self._network.get_timeslot()}')
            return True
        else:
            self.logger.log(f'Falha na transmissão de {num_qubits} qubits entre {alice_id} e {bob_id} após {attempts} tentativas. Timeslot: {self._network.get_timeslot()}')
            return False

    def teleportation_protocol(self, alice_id: int, bob_id: int):
        """
        Realiza o protocolo de teletransporte de um qubit de Alice para Bob.
        
        args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
        
        returns:
            bool : True se o teletransporte foi bem-sucedido, False caso contrário.
        """
        self._network.timeslot()  # Incrementa o timeslot para o protocolo de teletransporte
        self.logger.log(f'Timeslot {self._network.get_timeslot()}: Iniciando teletransporte entre {alice_id} e {bob_id}.')
        
        # Estabelece uma rota válida
        route = self._network_layer.short_route_valid(alice_id, bob_id)
        if route is None:
            self.logger.log(f'Não foi possível encontrar uma rota válida para teletransporte entre {alice_id} e {bob_id}. Timeslot: {self._network.get_timeslot()}')
            return False
        
        # Pega um qubit de Alice e um qubit de Bob
        alice = self._network.get_host(alice_id)
        bob = self._network.get_host(bob_id)
        
        if len(alice.memory) < 1 or len(bob.memory) < 1:
            self.logger.log(f'Alice ou Bob não possuem qubits suficientes para teletransporte. Timeslot: {self._network.get_timeslot()}')
            return False
        
        qubit_alice = alice.memory.pop(0)  # Remove o primeiro qubit da memória de Alice
        qubit_bob = bob.memory.pop()       # Remove o último qubit da memória de Bob
        
        # Calcula a fidelidade final do teletransporte
        f_alice = qubit_alice.get_current_fidelity()
        f_bob = qubit_bob.get_current_fidelity()
        
        # Assume fidelidade do link como a média das fidelidades dos pares EPR na rota
        fidelities = []
        for i in range(len(route) - 1):
            epr_pairs = self._network.get_eprs_from_edge(route[i], route[i+1])
            fidelities.extend([epr.get_current_fidelity() for epr in epr_pairs])
        
        if not fidelities:
            self.logger.log(f'Não foi possível encontrar pares EPR na rota entre {alice_id} e {bob_id}. Timeslot: {self._network.get_timeslot()}')
            return False
        
        f_route = sum(fidelities) / len(fidelities)
        
        # Fidelidade final do qubit teletransportado
        F_final = f_alice * f_bob * f_route + (1 - f_alice) * (1 - f_bob) * (1 - f_route)
        
        qubit_info = {
            'alice_id': alice_id,
            'bob_id': bob_id,
            'route': route,
            'fidelity_alice': f_alice,
            'fidelity_bob': f_bob,
            'fidelity_route': f_route,
            'F_final': F_final,
            'qubit_alice': qubit_alice,
            'qubit_bob': qubit_bob,
            'success': True
        }
        
        # Adiciona o qubit teletransportado à memória de Bob com a fidelidade final calculada
        qubit_alice.fidelity = F_final
        bob.memory.append(qubit_alice)
        self.logger.log(f'Teletransporte de qubit de {alice_id} para {bob_id} foi bem-sucedido com fidelidade final de {F_final}. Timeslot: {self._network.get_timeslot()}')
        
        # Par virtual é deletado no final
        for i in range(len(route) - 1):
            self._network.remove_epr(route[i], route[i + 1])
        
        self.transmitted_qubits.append(qubit_info)
        return True

    def avg_fidelity_on_transportlayer(self):
        """
        Calcula a fidelidade média de todos os qubits realmente utilizados na camada de transporte.

        returns:
            float : Fidelidade média dos qubits utilizados na camada de transporte.
        """
        total_fidelity = 0
        total_qubits_used = 0

        # Calcula a fidelidade dos qubits transmitidos e registrados no log de qubits transmitidos
        for qubit_info in self.transmitted_qubits:
            fidelity = qubit_info['F_final']
            total_fidelity += fidelity
            total_qubits_used += 1
            self.logger.log(f'Fidelidade do qubit utilizado de {qubit_info["alice_id"]} para {qubit_info["bob_id"]}: {fidelity}')

        # Considera apenas os qubits efetivamente transmitidos (não inclui os qubits que permanecem na memória dos hosts)
        if total_qubits_used == 0:
            self.logger.log('Nenhum qubit foi utilizado na camada de transporte.')
            return 0.0

        avg_fidelity = total_fidelity / total_qubits_used
        self.logger.log(f'A fidelidade média de todos os qubits utilizados na camada de transporte é {avg_fidelity}')
        
        return avg_fidelity


    def get_teleported_qubits(self):
        """
        Retorna a lista de qubits teletransportados.
        
        returns:
            list : Lista de dicionários contendo informações dos qubits teletransportados.
        """
        return self.transmitted_qubits

    def run_transport_layer(self, alice_id: int, bob_id: int, num_qubits: int):
        """
        Executa a requisição de transmissão e o protocolo de teletransporte.

        args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
            num_qubits : int : Número de qubits a serem transmitidos.

        returns:
            bool : True se a operação foi bem-sucedida, False caso contrário.
        """
        alice = self._network.get_host(alice_id)
        bob = self._network.get_host(bob_id)
        available_qubits = len(alice.memory)

        # Se Alice tiver menos qubits do que o necessário, crie mais qubits
        if available_qubits < num_qubits:
            qubits_needed = num_qubits - available_qubits
            self.logger.log(f'Número insuficiente de qubits na memória de Alice (Host {alice_id}). Criando mais {qubits_needed} qubits para completar os {num_qubits} necessários.')

            for _ in range(qubits_needed):
                self._network.timeslot()  # Incrementa o timeslot a cada criação de qubit
                self.logger.log(f"Timeslot antes da criação do qubit: {self._network.get_timeslot()}")
                self._physical_layer.create_qubit(alice_id)  # Cria novos qubits para Alice
                self.logger.log(f"Qubit criado para Alice (Host {alice_id}) no timeslot: {self._network.get_timeslot()}")

            # Atualiza a quantidade de qubits disponíveis após a criação
            available_qubits = len(alice.memory)

        # Certifique-se de que Alice tenha exatamente o número de qubits necessários após a criação
        if available_qubits != num_qubits:
            self.logger.log(f'Erro: Alice tem {available_qubits} qubits, mas deveria ter {num_qubits} qubits. Abortando transmissão.')
            return False

        # Começa a transmissão dos qubits
        max_attempts = 2
        attempts = 0
        success_count = 0

        while attempts < max_attempts and success_count < num_qubits:
            self.logger.log(f'Tentativa {attempts + 1} de transmissão de qubits entre {alice_id} e {bob_id}.')

            for _ in range(num_qubits - success_count):
                # Tenta encontrar uma rota válida
                route = self._network_layer.short_route_valid(alice_id, bob_id)

                if route is None:
                    self.logger.log(f'Não foi possível encontrar uma rota válida na tentativa {attempts + 1}. Timeslot: {self._network.get_timeslot()}')
                    break

                # Verifica a fidelidade dos pares EPR ao longo da rota
                fidelities = []
                for i in range(len(route) - 1):
                    node1 = route[i]
                    node2 = route[i + 1]


                    epr_pairs = self._network.get_eprs_from_edge(node1, node2)
                    if len(epr_pairs) == 0:
                        self.logger.log(f'Não foi possível encontrar pares EPR suficientes na rota {route[i]} -> {route[i + 1]}.')
                        break
                    fidelities.extend([epr.get_current_fidelity() for epr in epr_pairs])

                # Se falhar em encontrar pares EPR suficientes, tenta na próxima tentativa
                if len(fidelities) == 0:
                    attempts += 1
                    continue

                f_route = sum(fidelities) / len(fidelities)

                # Se a rota for encontrada, transmite o qubit imediatamente
                if len(alice.memory) > 0:  # Verifica se ainda há qubits na memória de Alice
                    qubit_alice = alice.memory.pop(0)  # REMOVE o qubit de Alice
                    f_alice = qubit_alice.get_current_fidelity()
                    F_final = f_alice * f_route

                    # Armazena informações sobre o qubit transmitido
                    qubit_info = {
                        'alice_id': alice_id,
                        'bob_id': bob_id,
                        'route': route,
                        'fidelity_alice': f_alice,
                        'fidelity_route': f_route,
                        'F_final': F_final,
                        'timeslot': self._network.get_timeslot(),
                        'qubit': qubit_alice
                    }

                    # Adiciona o qubit transmitido à memória de Bob
                    qubit_alice.fidelity = F_final
                    bob.memory.append(qubit_alice)

                    # Incrementa o contador de qubits e timeslot
                    success_count += 1
                    self.used_qubits += 1
                    self.logger.log(f'Teletransporte de qubit de {alice_id} para {bob_id} na rota {route} foi bem-sucedido com fidelidade final de {F_final}.')

                    # Armazena as informações do qubit transmitido
                    self.transmitted_qubits.append(qubit_info)
                else:
                    self.logger.log(f'Alice não possui qubits suficientes para continuar a transmissão.')
                    break

            attempts += 1

        if success_count == num_qubits:
            self.logger.log(f'Transmissão e teletransporte de {num_qubits} qubits entre {alice_id} e {bob_id} concluídos com sucesso. Timeslot: {self._network.get_timeslot()}')
            return True
        else:
            self.logger.log(f'Falha na transmissão de {num_qubits} qubits entre {alice_id} e {bob_id}. Apenas {success_count} qubits foram transmitidos com sucesso. Timeslot: {self._network.get_timeslot()}')
            return False




