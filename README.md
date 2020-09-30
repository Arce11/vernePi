# Proyecto vernePi

# Instrucciones (IDE)
OJO: Instrucciones para desarrollar desde Windows y sincronizar archivos con la Raspberry automáticamente (para no tener que transferir el código a pelo con cada cambio para ejecutar y probar). Por poder, se puede instalar un IDE en la raspberry y desarrollar ahí directamente, sincronizando con el repositorio y usándola como un PC corriente, pero no sé si irá algo lento...

--- En la Raspberry Pi ---
1. Crear carpeta para el repositorio en la raspberry
   1. mkdir vernePi
   1. cd vernePi
2. Comprobar versión de Python 3 incluida:
   1. python3 --version
3. Si es 3.7.X debería valer. Si no, instalar la última (y crear el entorno del paso 4 usando python3.7 en vez de python3):
   1. sudo apt-get install python3.7
4. Crear entorno virtual para instalar todo lo que vaya surgiendo, si surge. Guardarlo en carpeta venv para que el .gitignore la pille y no se suba al Git:
   1. python3 -m venv venv
  
--- En Windows ---
1. Instalar Git
2. Instalar IDE. Recomiendo PyCharm (creo que versión Pro está disponible con Uniovi, no sé si directamente o a través del pack de estudiante de GitHub), aunque otro debería valer en principio

--- En el IDE (Aquí instrucciones para PyCharm) ---
1. Configurar Git en el IDE. En PyCharm se llama VCS (Version Control System (?)):
   1. Con proyecto previamente abierto: File->Settings->Version Control
     1. Sin proyecto abierto: Configure->Settings->Version Control
   1. Git->  Aquí seleccionamos la ubicación del git.exe descargado antes
   1. GitHub->  Añadimos nuestra cuenta de GitHub
1. Si teníamos un proyecto abierto, lo cerramos. Cargamos el repositorio con "Check out from Version Control"->"Git" (URL: https://github.com/Arce11/vernePi.git )
1. Definimos el entorno de despliegue remoto
   1. Tools->Deployment->Configuration
   1. "+"->SFTP, Nombre de servidor: El que queramos (sólo para identificar la configuración)
   1. Host: dirección de la raspberry (raspberrypi por defecto, aunque puede interesar cambiarla...), Username: pi (por defecto), Password: raspberry (por defecto), tick en "Save password"
   1. Antes de darle a "OK", arriba vamos a la segunda pestaña ("Mappings")
   1. Local path: dirección del proyecto de PyCharm, Deployment Path: dirección de la carpeta donde queremos que se sincronicen los archivo
   1. Guardamos la configuración de "deployment"
   1. Volvemos a Tools->Deployment y activamos "Automatic upload" (si no, habría que sincronizar manualmente los cambios en cualquier archivo con la raspi)
1. Definimos el intérprete del proyecto como el de la propia raspberry. Podríamos usar uno local para ir empezando y ejecutar las cosas complicadas directamente por putty/escritorio remoto en la raspberry, pero eso daría problemas de detección de errores y de librerías no encontradas (como las del GPIO de la raspi)
   1. File->Settings->Project: <nombre de proyecto>->Project Interpreter-> "Icono de engranaje" -> Add
   1. SSH Interpreter->Existing server configuration-> Seleccionamos la configuración de "deployment" que definimos antes
1. Añadimos una configuración de ejecución para que sepa qué archivo lanzar y con qué intérprete (puede haber varios por proyecto):
   1. Arriba a la derecha damos a "Edit Configurations"
   1. "+"->Python
   1. Seleccionamos en "Script Path" el archivo que esa configuración lanzará (podemos tener una config. principal que apunte a un "main.py", y otra para probar cosillas rápidas que apunte a un "test.py", por ej.)
   1. Verificamos que en "Python Interpreter" está el "Remote Python" configurado antes

--- De vuelta en la Raspberry (OJO: tanto si se está usando el montaje descrito con Pycharm+Windows como si se está clonando el repositorio directamente en la raspi) ---
1. Se activa el entorno virtual (desde la carpeta de proyecto, o donde esté el entorno virtual): source venv/bin/activate
1. Se instalan las dependencias: pip install -r requirements.txt

Con todo esto y si se alinean los astros, deberíamos poder darle al típico botón de "Run" y ver la salida por consola en Windows, pero estar ejecutándolo en la raspi. Al ser por consola SSH, esto no vale si tenemos algún tipo de GUI. En ese caso, habría que en vez de darle a "Run", ir a la raspi por putty (si no hay GUI) o VNC y lanzar el script desde ahí. Los archivos se sincronizarían automáticamente, por lo que debería ser casi igual de cómodo.
  OJO: recordar para ejecutar desde la raspi el "source venv/bin/activate" y el "deactivate" para (des)activar el entorno virtual de python.
