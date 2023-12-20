import PySimpleGUI as gui
import json
import subprocess as terminal
import time
import random

# Standart configurations
config = {
	'theme': "Python",
	'vnc_port': 8080,
	'vncviewer': "flatpak run --filesystem= org.tigervnc.vncviewer",
	'passwd_temp': "",
	'random': 8,
	'passwd_type': 0,
	'containers': []
}
# Container example:
# {
# 'name': 'example:latest'
# 'vnc': 8080,
# 'passwd': "password",
# 'terminal': False,
# 'src': '/file/in/the/host',
# 'dst': '/dst/in/container',
# 'args': []
# }

#Password type:
# 0: Creates a passwd file that will be read by viewer AND put the password to container using - e SENHA=password
# 1: Creates a passwd file that will be read by viewer only
# 2: put the password to container using - e SENHA=password only
# 3: Nothingh


# The configuration file
config_file = "config_containers.json"

########################## Save the configurations into file ####################################################
def save():
	with open(config_file, 'w') as file:
		if ask("Salvar configurações ?"):
			json.dump(config, file)
			warning("Novas configurações salvas:", config)
			return True
		return False

######################## The main loop of program ###############################################################
def main():
	lines = []
	if config['containers']:
		for container in config['containers']:
			lines.append([gui.Text(container['name']), gui.Button("▶️", key=container['name']+">"), gui.Button("⚙️", key=container['name']+"C")])
	else:
		lines = [gui.Text("Adicione mais containers !")]
	layout = [[gui.Button("⚙️ Configurações gerais"), gui.Button("➕ Adicionar Imagem"), gui.Button("▐▐ Remover Containers.")], lines]
	window = gui.Window('Containers', layout, resizable=True)
	while True:
		event, values = window.read() # read events
		if event == gui.WIN_CLOSED: # if the user close the program
			window.close()
			raise SystemExit
		elif event is None: # if nothingh was pressed
			continue
		elif event == "⚙️ Configurações gerais": # configurations
			configurations()
			break
		elif event == "➕ Adicionar Imagem":
			change_container(None)
			break
		elif event == "▐▐ Remover Containers.":
			if ask("Excluir todos os containers no docker 'docker rm -f $(docker ps -aq)' ?"):
				data = terminal.run('docker rm -f $(docker ps -aq)', shell=True, capture_output=True, text=True)
				warning("Containers excluídos !", data)
				break
		else: # the user want to start or configure a container
			if event[-1] == ">":
				start_container(event[:-1])
				break
			else:
				change_container(event[:-1])
				break
	window.close()

###################### Add or change the start script of a container ############################################
def change_container(name):
	layout = [
		[gui.Text("Nome:"), gui.Input(default_text="O nome da imagem a ser executada.", key="NAME")],
		[gui.Checkbox('Usar Vnc ?', key="VNC")],
		[gui.Text("Porta VNC:"), gui.Input(default_text="A porta que o servidor VNC está usando dentro do container.", key="PORT")],
		[gui.Text("Senha VNC:"), gui.Input(default_text="A senha que deve ser usada para acessar o vnc.", key="PASS")],
		[gui.Checkbox('Usar Terminal ?', key="T")],
		[gui.Checkbox('Montar pasta ?', key="M")],
		[gui.Text("Caminho no Host:"), gui.Input(default_text="Caminho absoluto da pasta a ser montada.", key="SRC")],
		[gui.Text("Caminho no Container:"), gui.Input(default_text="Caminho absoluto do destino da pasta.", key="DST")],
		[gui.Checkbox('Argumentos extras ?', key="A")],
		[gui.Text("Argumentos:"), gui.Input(default_text="Argumentos extras para rodar a imagem.", key="ARG")],
		[gui.Button("Criar"), gui.Button("Cancelar")]
	]
	container = None
	if name is not None:
		for item in config['containers']:
			if item['name'] == name:
				container = item
				break
		layout = [
			[gui.Text(f"Editando: {name}")],
			[gui.Checkbox('Usar Vnc ?', key="VNC", default=container['vnc'] != "")],
			[gui.Text("Porta VNC:"), gui.Input(default_text=container['vnc'], key="PORT")],
			[gui.Text("Senha VNC:"), gui.Input(default_text=container['passwd'], key="PASS")],
			[gui.Checkbox('Usar Terminal ?', key="T", default=container['terminal'])],
			[gui.Checkbox('Montar pasta ?', key="M", default=(container['src'] != "" and container['dst'] != ""))],
			[gui.Text("Caminho no Host:"), gui.Input(default_text=container['src'], key="SRC")],
			[gui.Text("Caminho no Container:"), gui.Input(default_text=container['dst'], key="DST")],
			[gui.Checkbox('Argumentos extras ?', key="A", default=container['args'] != "")],
			[gui.Text("Argumentos:"), gui.Input(default_text=container['args'], key="ARG")],
			[gui.Button("Mudar"), gui.Button("Cancelar")],
			[gui.Button("Exclúir container.")]
		]
	window = gui.Window('Gerenciador de containers', layout, resizable=True)
	while True:
		event, values = window.read()
		if event == "Cancelar" or event == gui.WIN_CLOSED:
			warning("Operação Cancelada.", "Nenhuma alteração foi feita.")
			break
		if event == "Exclúir container.":
			if ask("Apagar essa configuração ?"):
				config['containers'].remove(container)
				if save():
					break
				config['containers'].append(container)
		if event == "Mudar" or event == "Criar":
			if event == "Criar":
				name = values['NAME']
			new_container = {'name': name,}
			
			if values['VNC']:
				new_container['vnc'] = values['PORT']
				new_container['passwd'] = values['PASS']
			else:
				new_container['vnc'] = ""
				new_container['passwd'] = ""
				
			new_container['terminal'] = values['T']
			
			if values['M']:
				new_container['src'] = values['SRC']
				new_container['dst'] = values['DST']
			else:
				new_container['src'] = ""
				new_container['dst'] = ""
				
			new_container['args'] = values['ARG'] if values['A'] else ""
			
			if event == "Mudar":
				config['containers'].remove(container)
			config['containers'].append(new_container)
			if save():
				break
			config['containers'].remove(new_container)
			if event == "Mudar":
				config['containers'].append(container)
	window.close()

###################### Start a container and the VNC viewer (if configured to) ##################################
def start_container(name):
	global config
	dictionary = None
	password = None
	for item in config['containers']:
		if item['name'] == name:
			dictionary = item
			break
	command = ["docker", "run", "--rm"]
	if dictionary['src'] != "" and dictionary['dst'] != "":
		command += ["--mount", f"type=bind,source={dictionary['src']},target={dictionary['dst']}"]
	if dictionary['args'] != "":
		command += dictionary['args'].split()

	if dictionary['vnc'] != "":
		command += ["-p", f"{config['vnc_port']}:{dictionary['vnc']}"]
		if dictionary['passwd'] != "":
			password = dictionary["passwd"]
		else:
			password = ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(config['random']))
		if config['passwd_type'] == 0 or config['passwd_type'] == 2:
			command += ["-e", f'SENHA={password}']

	if dictionary['terminal']:
		command += ["-it", name]
		command = ["gnome-terminal", "--"] + command
		print(command)
		terminal.Popen(command)
	else:
		command += ["-d", name]
		container = terminal.run(command, capture_output=True)
		if container.returncode != 0:
			warning("Falha ao rodar imagem:", container)
			return
		
	if dictionary['vnc'] != "":
		viewer = config['vncviewer'].split()
		if config['passwd_temp'] != "" and (config['passwd_type'] == 0 or config['passwd_type'] == 1):
			create_passwd(password)
			viewer += [
				"-passwd",
				config['passwd_temp']+"/passwd"
			]
		viewer.append(f"localhost:{config['vnc_port']}")
		print(viewer)
		time.sleep(1.8)
		terminal.run(viewer)
	else:
		warning("O container está rodando:", container)
		
###################### Create a passwd file of Tiger VNC ########################################################
def create_passwd(password):
	process = terminal.Popen(["tigervncpasswd", "-f"], stdin=terminal.PIPE, stdout=terminal.PIPE, stderr=terminal.PIPE)
	output, error = process.communicate(input=password.encode())
	if error is not None and error != b'':
		warning("Erro ao criar senha:", error)
	with open (str(config['passwd_temp']+"/passwd"), 'wb') as file:
		file.write(output)
	
###################### Window to configure options about passwords ##############################################
def vnc_passwd():
	global config
	layout = [
		[gui.Text("Quantidade de caracteres para senhas aleatórias:")],
		[gui.Text("Geradas quando o campo de senha está vazio.", font=('Helvetica', 8))],
		[gui.Slider(key="RANDOM",range=(8,20), default_value=config['random'], orientation='horizontal', size=(20,5), font=('Helvetica', 8))],
		[gui.Radio("Usar '-e SENHA=...' no servidor e arquivo no visualizador.", "CONFIG", default=config['passwd_type']==0, key="r0"), gui.Radio("Senha apenas no visualizador.", "CONFIG", default=config['passwd_type']==1, key="r1")],
		[gui.Radio("Senha apenas no servidor com '-e SENHA=...'.", "CONFIG", default=config['passwd_type']==2, key="r2"), gui.Radio("Sem senha.", "CONFIG", default=config['passwd_type']==3, key="r3")],
		[gui.Button("Confirmar"), gui.Button("Cancelar")]
	]
	window = gui.Window('Configurações de senhas', layout, resizable=True)
	while True:
		event, values = window.read()
		if event == gui.WIN_CLOSED or event == "Cancelar": # if the user close the window or cancell
			break
		if event == "Confirmar":
			old_random = config['random']
			old_passwd = config['passwd_type']
			config['random'] = values['RANDOM']
			if values['r0']:
				config['passwd_type'] = 0
			elif values['r1']:
				config['passwd_type'] = 1
			elif values['r2']:
				config['passwd_type'] = 2
			elif values['r3']:
				config['passwd_type'] = 3
			if save():
				break
			config['random'] = old_random
			config['passwd_type'] = old_passwd
	window.close()

###################### Open the configurations window ###########################################################
def configurations():
	global config
	layout = [
		[gui.Text("Porta padrão do VNC:"), gui.Button(config['vnc_port'], key="PORT")],
		[gui.Text("Comando para abrir visualizador:"), gui.Button(config['vncviewer'], key="VIEWER")],
		[gui.Text("Pasta para armazenar senhas:"), gui.Button(config['passwd_temp'], key="TEMP")],
		[gui.Button("Senhas para VNC.")],
		[gui.Button("Mudar tema do app.")],
		[gui.Button("Excluir imagens <none>.")],
		[gui.Button("Resetar configurações.")],
		[gui.Text("Feito por: thiago1255")]
	]
	window = gui.Window('Configurações', layout, resizable=True)
	while True:
		event, values = window.read()
		if event == gui.WIN_CLOSED: # if the user close the window
			window.close()
			break
		if event == "PORT":
			port_config()
			break
		if event == "VIEWER":
			vnc_config()
			break
		if event == "TEMP":
			temp_config()
			break
		if event == "Senhas para VNC.":
			vnc_passwd()
			break
		if event == "Mudar tema do app.":
			themes()
			break
		if event == "Excluir imagens <none>.":
			if ask("Excluir imagens marcadas como <none> ? "):
				data = terminal.run('docker rmi $(docker images -f "dangling=true" -q)', shell=True, capture_output=True, text=True)
				warning("Imagens excluídas !", data)
				break
		if event == "Resetar configurações.":
			if ask("Resetar configurações do aplicativo ?"):
				if ask("Realmente apagar ?"):
					terminal.run(["rm", f"{config_file}"])
					warning("Configurações resetadas !", "O arquivo foi apagado.")
					config = None
				else:
					warning("Operação Cancelada.", "Nenhuma alteração foi feita.")
			else:
				warning("Operação Cancelada.", "Nenhuma alteração foi feita.")
			break
	gui.theme(config['theme'])
	window.close()

###################### The configuration window for temp. passwd. folder ########################################
def temp_config():
	old_folder = config['passwd_temp']
	layout = [
		[gui.Text("Pasta para senhas:", font=(22))],
		[gui.Input(default_text=old_folder)],
		[gui.Button("Confirmar"), gui.Button("Cancelar")],
		[gui.Text("Essa será a pasta onde sera armazenado temporariamente o arquivo 'passwd'.")]
	]
	window = gui.Window('Configurações', layout, resizable=True)
	while True:
		event, values = window.read()
		if event == gui.WIN_CLOSED or event == "Cancelar":
			warning("Operação Cancelada.", "Nenhuma alteração foi feita.")
			break
		if event == "Confirmar":
			config['passwd_temp'] = values[0]
			if not save():
				config['passwd_temp'] = old_folder
			break
	window.close()
	
###################### The configuration window for vnc port ####################################################
def port_config():
	old_port = config['vnc_port']
	layout = [
		[gui.Text("Porta padrão do VNC:", font=(22))],
		[gui.Input(default_text=old_port)],
		[gui.Button("Confirmar"), gui.Button("Cancelar")],
		[gui.Text("Essa será a porta que o visualizador VNC irá usar (localhost:PORTA).")]
	]
	window = gui.Window('Configurações', layout, resizable=True)
	while True:
		event, values = window.read()
		if event == gui.WIN_CLOSED or event == "Cancelar":
			warning("Operação Cancelada.", "Nenhuma alteração foi feita.")
			break
		if event == "Confirmar":
			config['vnc_port'] = int(values[0])
			if not save():
				config['vnc_port'] = old_port
			break
	window.close()

###################### The configuration window for vnc viewer ##################################################
def vnc_config():
	old = config['vncviewer']
	layout = [
		[gui.Text("Visualizador VNC:", font=(22))],
		[gui.Input(default_text=old)],
		[gui.Button("Confirmar"), gui.Button("Cancelar")],
		[gui.Text("Esse será o comando que abrirá o visualizador VNC.")]
	]
	window = gui.Window('Configurações', layout, resizable=True)
	while True:
		event, values = window.read()
		if event == gui.WIN_CLOSED or event == "Cancelar":
			warning("Operação Cancelada.", "Nenhuma alteração foi feita.")
			break
		if event == "Confirmar":
			config['vncviewer'] = values[0]
			if not save():
				config['vncviewer'] = old
			break
	window.close()

###################### An window that ask if the user want continue #############################################
def ask(text):
	layout = [
		[gui.Text(text)],
		[gui.Button('Sim'), gui.Button('Não')]
	]
	window = gui.Window("Confirmação:", layout)
	while True:
		e, v = window.read()
		if e == "Não" or e == gui.WIN_CLOSED:
			window.close()
			warning("Operação Cancelada.", "Nenhuma alteração foi feita.")
			return False
		if e == "Sim":
			window.close()
			return True

###################### Just an window with an warning ###########################################################
def warning(text, data):
	layout = [
		[gui.Text(text, font=(20))],
	]
	if isinstance(data, terminal.CompletedProcess):
		if data.stdout != "":
			layout += [
				[gui.Text("Saída:")],
				[gui.Multiline(data.stdout, size=(50, data.stdout.count('\n')+1))],
			]
		if data.stderr != "":
			layout += [
				[gui.Text("Erros:")],
				[gui.Multiline(data.stderr, size=(50, data.stderr.count('\n')+1))]
			]
	else:
		layout.append([gui.Text(data)])
	layout.append([gui.Button('Ok')])
	window = gui.Window("Aviso:", layout, resizable=True)
	while True:
		e, v = window.read()
		if e == "Ok" or e == gui.WIN_CLOSED:
			window.close()
			return

###################### Open the themes selection window #########################################################
def themes():
	old_theme = config['theme']
	lines = []
	temp_line = []
	for theme in gui.theme_list():
		temp_line.append(gui.Button(theme))
		if len(temp_line) == 9:
			lines.append(temp_line)
			temp_line = []
	lines.append(temp_line)
	layout = [[gui.Text("Selecione um tema;")], lines]
	window = gui.Window('Temas', layout, resizable=True)
	while True:
		event, values = window.read() # read events
		if event == gui.WIN_CLOSED: # if the user close the window
			break
		elif event is None: # if nothingh was pressed
			continue
		else: # a theme was selected
			config['theme'] = event
			gui.theme(config['theme'])
			if save():
				break
			else:
				config['theme'] = old_theme
				gui.theme(config['theme'])
				break
	window.close()

###################### Start the program ########################################################################
try:
	with open(config_file, 'r') as file:
		config = json.load(file)
		gui.theme(config['theme'])
		print(f"O programa iniciou com as seguintes configurações: {config}")
except: # If no configuration was found
	save()

while True:
	if config is None:
		raise SystemExit
	main()
