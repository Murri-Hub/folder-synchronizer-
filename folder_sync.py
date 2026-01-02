import os                 #Modulo standard pensato per interagire con il sistema operativo (OS)
import shutil             #Modulo standard pensato per operazioni di "alto livello" con i file
import hashlib            #Modulo standard che permette l'uso dell'hash per riconoscere con certezza la sincronizzazione dei
from pathlib import Path    #Importa la classe Path dal modulo pathlib per lavorare con i percorsi limitando errori dovuti ad interpretazioni di Python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
#Importa la funzione as_completed che permette di lavorare con i file nell'ordine in cui sono stati processati, e le classi per lavorare
#con thread e multiprocessing
from multiprocessing import cpu_count   #Importa la funzione per conoscere il numero di processori a disposizione
import time               #Modulo standard pensato per lavorare con il tempo

class FolderSynchronizer:
    """
    Classe per sincronizzare due cartelle usando threading e multiprocessing.
    """

    def __init__(self, source, destination, workers=4, use_hash=False):
        """
        Inizializza il sincronizzatore.

        Args:
            source: Percorso cartella sorgente
            destination: Percorso cartella destinazione
            workers: Numero di thread/processi paralleli (default: 4)
            use_hash: Se True, usa hash MD5 per verificare i file (più lento ma più sicuro)
        """
        self.source = Path(source)
        self.destination = Path(destination)
        self.workers = workers
        self.use_hash = use_hash

        # Statistiche
        self.files_copied = 0
        self.files_deleted = 0
        self.errors = []

# ==================== CALCOLO HASH ======================

    def calcola_hash(self, filepath):
        """
        Metodo che calcola l'hash di un file con algoritmo MD5 (operazione CPU-intensive).
        Verrà utilizzato con multiprocessing nel metodo "verifica_con_hash".

        Argomenti in ingresso:
            filepath: Percorso del generico file

        Returns:
            Tupla (filepath, hash_string, success)
        """
        try:
            hash_md5 = hashlib.md5()  #Elemento per processare dati e calcolare hash tramite "hashlib" con agoritmo MD5
            chunk_size = 1024 * 1024  #Ogni pezzo di file processato sarà di 1MB

            #Il file verrà aperto e letto a pezzi per non occupare troppa RAM durante la lettura
            with open(filepath, "rb") as f:  #Apertura e successiva chiusura del file con lettura in modalità binaria per calcolo hash

                while True:
                    chunk = f.read(chunk_size)  #Lettura pezzo di file di dimensione "chunk_size" = 1 MB
                    if not chunk:
                        break  #Il ciclo while si chiude quando l'elemento chunk è vuoto

                    hash_md5.update(chunk)  #Aggiorna gradualmente l'hash del file man mano che si aggiungono i chunk

            return filepath, hash_md5.hexdigest(), True  #Restituisce il percorso del file e l'hash in formato esadecimale più il boolean True in "success"

        except Exception as e:
            return filepath, None, False  #Restituisce la tupla con il percorso, senza l'hash ed il boolean False in "success"

# ==================== COPIA FILE ======================

    def copia_file(self, src_file, dst_file):
        """
        Metodo che copia un singolo file (operazione I/O-intensive).
        Verrà utilizzato con threading nel metodo "sync" alla fase 2.

        Argomenti in ingresso:
            src_file: Percorso file sorgente
            dst_file: Percorso file destinazione

        Returns:
            Tupla (success, message)
        """

        #Estrazione della (sotto)cartella che contiene il file dal percorso completo
        dst_folder = os.path.dirname(dst_file)

        try:
            #Verifica l'esistenza della cartella nella destinazione e la crea se non esiste
            if not os.path.exists(dst_folder):
                os.makedirs(dst_folder)

            #Copia il file con metadati
            shutil.copy2(src_file, dst_file)

            return True, f"\nCopiato: {Path(src_file).name}"  #Restituisce un True ed un messaggio di operazione andata a buon fine

        except Exception as e:
            return False, f"\nErrore copiando {Path(src_file).name}: {str(e)}"  #Restituisce un False e relativo messaggio

# ==================== ELIMINA FILE ======================

    def elimina_file(self, file_path):
        """
        Metodo che elimina un singolo file.
        Verrà utilizzato con threading nel metodo "sync" alla fase 3.

        Argomenti in ingresso:
            file_path: Percorso del file da eliminare

        Returns:
            Tupla (success, message)
        """
        try:  #Elimina file e restituisce il True in "success" con relativo messaggio
            os.remove(file_path)
            return True, f"\nEliminato: {Path(file_path).name}"

        except Exception as e:  #In caso di eccezione restituisce il False in "success" con relativo messaggio

            return False, f"\nErrore eliminando {Path(file_path).name}: {str(e)}"

# ==================== TROVA FILE ======================

    def trova_file_da_sincronizzare(self):
        """
        Metodo che scansiona le cartelle e identifica quali file devono essere copiati.
        Viene utilizzato nel metodo "sync" alla fase 1.

        Returns:
            Lista di tuple (src_file, dst_file) dei file da copiare
        """
        files_da_copiare = []  #Inizializza la lista da riempire con le tuple

        print("\nScansione cartelle in corso...")

        """
        Nel ciclo for successivo:
        walk() dalla libreria os percorre una cartella restituendo la seguente tupla: (root, dirs, files)
        "root" contiene il percorso completo della cartella
        "dirs" contiene una lista con i nomi delle sottocartelle in root
        "files" contiene una lista con i nomi dei file in root
        I nomi sono convenzionali di Python
        Il seguente ciclo funziona quindi con una tupla relativa alla cartella source e quelle relative alle sottocartelle
        Ciascuna tupla contiene il percorso della cartella, la lista con le sottocartelle in essa contenute e la lista con i
        file in essa contenuti
        """

        for root, dirs, files in os.walk(self.source):

            #"rel_path" è il percorso relativo di "root" rispetto a "source",
            #in altre parole, ciò che manca al percorso "source" per diventare "root"
            rel_path = os.path.relpath(root, self.source)

            #"dst_path" è il percorso della cartella "destination" o contenuta in "destination" analogo a "root"
            #La "join()" serve per aggiungere il 'pezzo di percorso' "rel_path" al percorso "destination"
            dst_path = os.path.join(self.destination, rel_path)

            #La riga seguente verifica che la cartella del percorso "dst_path" esista, prima di procedere
            os.makedirs(dst_path, exist_ok=True)

            """
            Il seguente ciclo scorre la lista "files" presente nella tupla e definisce 2 elementi per ogni file
            Uno contiene il percorso completo del file nella cartella lato sorgente
            L'altro contiene il percorso completo dello stesso file nella cartella lato destinazione
            """

            for file in files:
                src_file = os.path.join(root, file)  #join che crea il percorso completo del file a partire dalla root
                dst_file = os.path.join(dst_path, file)  #join per il file analogo nella cartella di destinazione

                #Verifica se il file deve essere copiato verificando prima l'esistenza
                if not os.path.exists(dst_file):

                    #File non esiste nella destinazione
                    files_da_copiare.append((src_file, dst_file))

                elif not self.use_hash:  #Se "use_hash" è False, si fa una verifica della datà come modalità di controllo rapido senza hash

                    #Controllo semplice: data di modifica
                    if os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                        files_da_copiare.append((src_file, dst_file))

                """
                Il controllo con getmtime() sarà l'unico eseguito, per maggiore rapidità, in caso si decida di
                non ricorrere all'uso dell'hash.
                """

        return files_da_copiare  #Restituisce la lista di tuple relative ai file da copiare

# ==================== VERIFICA HASH ======================

    def verifica_con_hash(self, files_da_verificare):
        """
        Metodo che verifica l'uguaglianza dei file usando hash MD5 (usa multiprocessing).
        Viene utilizzato nel metodo "sync" alla fase 1.

        Args:
            files_da_verificare: Lista di tuple (src_file, dst_file)

        Returns:
            Lista di tuple (src_file, dst_file) dei file che sono diversi
        """
        if not files_da_verificare:  #Se non ci sono file da verificare, restituisce una lista vuota in uscita
            return []

        print(f"\nCalcolo hash per {len(files_da_verificare)} file...")

        #Prepara lista di tutti i file da hashare
        files_to_hash = []  #Inizializza lista di file di cui calcolare l'hash

        for src, dst in files_da_verificare:  # Aggiunge alla lista tutti i file da sorgente e destinazione
            files_to_hash.append(src)
            files_to_hash.append(dst)

        #Inizializza il dizionario dove inserire i valori hash con i percorsi dei file come chiave
        hashes = {}

        #Calcola hash in parallelo usando tutti i core CPU
        with ProcessPoolExecutor(max_workers=cpu_count()) as executor:  #La classe ProcessPoolExecutor utilizza il numero massimo di processori a disposizione

            #Nel dizionario seguente vengono inseriti i future degli hash come chiavi e i percorsi dei file come chiavi
            future_to_file = {
                executor.submit(self.calcola_hash, f): f    #Invia il task il calcolo dell'hash al ProcessPoolExecutor con il metodo submit()
                                                            #Questo crea una chiave "future", cioè l'oggetto che conterrà l'hash alla fine della task
                for f in files_to_hash                      #Per ogni file, inserito come relativo valore nel dizionario
            }

            completati = 0  #Inizializza il numero di file completati

            for future in as_completed(future_to_file):  #Assegna a "future" i valori di "future_to_file" in ordine di processing (as_completed())

                filepath, hash_value, success = future.result()   #Da ogni "future" viene estratta una tupla con 3 valori che vengono assegnati ai rispettivi items
                                                                  #Il metodo result() aspetta la fine della task chiamata col metodo submit()
                completati += 1

                if success:  #Verifica che la variabile "success" sia True
                    hashes[filepath] = hash_value  #Salva l'hash come valore nel dizionario "hashes" usando il filepath come chiave

                    if completati % 10 == 0:  #Mostra progresso ogni 10 file
                        print(f"\nHash calcolati: {completati}/{len(files_to_hash)}")
                else:
                    print(f"\nErrore calcolando hash per {Path(filepath).name}")

        #Confronto degli hash
        files_diversi = []  #Inizializza la lista di quei file tali che quello in destinazione è diverso dal relativo file nella sorgente

        for src, dst in files_da_verificare:      #Prende la lista in ingresso al metodo per un check sui percorsi
            if src in hashes and dst in hashes:   #Se "hashes" contiene sia il file di sorgente che il relativo di destinazione
                if hashes[src] != hashes[dst]:    #Se i loro valori di hash sono diversi
                    files_diversi.append((src, dst))  # La lista viene aggiornata con i file in questione
            else:
                files_diversi.append((src, dst))  #Se non siamo riusciti a calcolare l'hash, aggiungiamo ugualmente il percorso del file alla lista

        print(f"\n{len(files_diversi)} file necessitano aggiornamento")

        return files_diversi  #Restituisce in uscita la lista creata

# ==================== FILE DA ELIMINARE ======================

    def trova_file_da_eliminare(self):
        """
        Metodo che trova i file nella destinazione che non esistono nella sorgente.
        Viene utilizzato nel metodo "sync" alla fase 3.

        Returns:
            Lista di percorsi dei file da eliminare
        """
        files_da_eliminare = []  # Inizializza la lista da riempire con i percorsi dei file da eliminare

        """
        Nel ciclo for successivo:
        walk() dalla libreria os percorre una cartella restituendo la seguente tupla: (root, dirs, files)
        "root" contiene il percorso completo della cartella
        "dirs" contiene una lista con i nomi delle sottocartelle in root
        "files" contiene una lista con i nomi dei file in root
        I nomi sono convenzionali di Python
        Il seguente ciclo funziona quindi con una tupla relativa alla cartella destination e quelle relative alle sottocartelle
        Ciascuna tupla contiene il percorso della cartella, la lista con le sottocartelle in essa contenute e la lista con i
        file in essa contenuti
        """

        for root, dirs, files in os.walk(self.destination):

            #"rel_path" è il percorso relativo di "root" rispetto a "source",
            #in altre parole, ciò che manca al percorso "source" per diventare "root"
            rel_path = os.path.relpath(root, self.destination)

            #"dst_path" è il percorso della cartella "destination" o contenuta in "destination" analogo a "root"
            #La "join()" serve per aggiungere il 'pezzo di percorso' "rel_path" al percorso "destination"
            src_path = os.path.join(self.source, rel_path)

            """
            Il seguente ciclo scorre la lista "files" presente nella tupla e definisce 2 elementi per ogni file
            Uno contiene il percorso completo del file nella cartella lato sorgente
            L'altro contiene il percorso completo dello stesso file nella cartella lato destinazione
            """

            for file in files:
                dst_file = os.path.join(root, file)  #join che crea il percorso completo del file a partire dalla root
                src_file = os.path.join(src_path, file)  #join per il file analogo nella cartella di destinazione

                if not os.path.exists(src_file):         #Verifica lato sorgente l'esistenza del percorso del file da eliminare
                    files_da_eliminare.append(dst_file)  #Aggiunge il file lato destinazione nella lista dei file da eliminare

        return files_da_eliminare

# ==================== SINCRONIZZATORE ======================

    def sync(self):
        """
        Metodo che esegue la sincronizzazione completa.
        Viene utilizzato nel "main".
        """
        start_time = time.time()  #Salva il momento di inizio sincronizzazione

        print("=" * 60)
        print("INIZIO SINCRONIZZAZIONE")
        print("=" * 60)
        print(f"Sorgente: {self.source}")
        print(f"Destinazione: {self.destination}")
        print(f"Workers: {self.workers}")
        print(f"Verifica hash: {'Sì' if self.use_hash else 'No'}")
        print("=" * 60)

        #FASE 1: Trova i file da sincronizzare
        files_da_copiare = self.trova_file_da_sincronizzare()

        #Se usa hash, verifica quali sono effettivamente diversi
        if self.use_hash and files_da_copiare:

            #Filtra solo i file che esistono già (per verificarli con hash)

            files_esistenti = [(s, d) for s, d in files_da_copiare
                               if os.path.exists(d)]  #Il file viene aggiunto nella lista di file esistenti se esiste nella destinazione

            files_nuovi = [(s, d) for s, d in files_da_copiare
                           if not os.path.exists(d)]  #Il file viene aggiunto nella lista di file da aggiungere se non esiste nella destinazione

            if files_esistenti:  # Se la lista contiene elementi
                files_modificati = self.verifica_con_hash(files_esistenti)  # Si fa la verifica di uguaglianza tramite l'hash dei file esistenti
                files_da_copiare = files_nuovi + files_modificati  # Si aggiungono i file nuovi

            else:
                files_da_copiare = files_nuovi  # Altrimenti ci sono solo file nuovi da aggiungere

        #FASE 2: Copia file in parallelo - Threading
        if files_da_copiare:  #Se ci sono file da copiare

            print(f"\nCopiando {len(files_da_copiare)} file...")

            with ThreadPoolExecutor(max_workers=self.workers) as executor:  #I file vengono processati tramite thread

                future_to_file = {
                    executor.submit(self.copia_file, src, dst): (src, dst)  #Anche qua, il metodo submit() manda la task al ThreadPoolExecutor creando una chiave "future"
                    for src, dst in files_da_copiare                        #Per ogni file da copiare, inserito come relativo valore nel dizionario
                }

                for future in as_completed(future_to_file):  #Ciclo che conta i processi completati e gli errori prendendo i future man mano che vengono completati

                    success, message = future.result()  #Il metodo result() prende il risultato del future come tupla composta da un tipo boolean ed un messaggio
                                                        #Il messaggio è utile in caso di errore, il quale viene indicato e può essere stampato

                    if success:  #Se la variabile "success" è True, aggiorna il numero di file copiati
                        self.files_copied += 1  #Aggiorna il contatore dei file copiati, inizializzato nella definizione della classe FolderSynchronizer
                        print(f"  {message}")
                    else:
                        self.errors.append(message)   #Altrimenti aggiunge il messaggio di errore alla lista "errors" e lo stampa
                        print(f"  {message}")

            print(f"\nCopiati {self.files_copied} file")  #Stampa l'informazione con il numero di files copiati

        else:
            print("\nNessun file da copiare")  # Se non ci sono file da copiare

        #FASE 3: Elimina file superflui
        files_da_eliminare = self.trova_file_da_eliminare()

        if files_da_eliminare:  #Se ci sono file da eliminare

            print(f"\nEliminando {len(files_da_eliminare)} file superflui...")

            with ThreadPoolExecutor(max_workers=self.workers) as executor:  #File processati con thread

                future_to_file = {
                    executor.submit(self.elimina_file, f): f  #Dizionario contenente i future ed i percorsi dei file da eliminare
                    for f in files_da_eliminare
                }

                for future in as_completed(future_to_file):  #Ciclo che conta i processi completati e gli errori
                    success, message = future.result()

                    if success: #Se la variabile "success" è True, aggiorna il numero di file cancellati
                        self.files_deleted += 1   #Aggiorna il contatore dei file eliminati, inizializzato nella definizione della classe FolderSynchronizer
                        print(f"  {message}")
                    else:
                        self.errors.append(message)   #Altrimenti aggiunge il messaggio di errore alla lista "errors" e lo stampa
                        print(f"  {message}")

            print(f"\nEliminati {self.files_deleted} file") #Stampa l'informazione con il numero di files eliminati

        else:
            print("\nNessun file da eliminare")  #Se non ci sono file da eliminare

        #RIEPILOGO

        elapsed_time = time.time() - start_time  #Tempo trascorso come momento attuale meno momento iniziale

        print("\n" + "=" * 60)
        print("RIEPILOGO SINCRONIZZAZIONE")
        print("=" * 60)
        print(f"File copiati: {self.files_copied}")
        print(f"File eliminati: {self.files_deleted}")
        print(f"Errori: {len(self.errors)}")
        print(f"Tempo impiegato: {elapsed_time:.2f} secondi")
        print("=" * 60)

        if self.errors:  #Se ci sono stati errori

            print("\nERRORI RISCONTRATI:")
            for error in self.errors:
                print(f"  {error}")  #Stampa tutti gli errori riscontrati

        print("\nSincronizzazione completata!")


# ==================== MAIN ======================

if __name__ == "__main__":

    #Inserire i percorsi delle cartelle
    source_folder = Path(r"Sorgente")
    destination_folder = Path(r"Destinazione")

    #Si spiega la possibilità di scegliere se usare l'hash oppure no
    print("\nScegli modalità di sincronizzazione:")
    print("1. Veloce (controllo data/dimensione)")
    print("2. Sicura (verifica hash MD5)")

    scelta = input("\nInserisci 1 o 2: ").strip()

    use_hash = (scelta == "2")    #Se la scelta è uguale a 2 (True) verrà utilizzato il calcolo dell'hash

    #Crea il sincronizzatore
    syncer = FolderSynchronizer(
        source=source_folder,
        destination=destination_folder,
        workers=4,  # Usa 4 thread/processi paralleli
        use_hash=use_hash
    )

    #Esegui la sincronizzazione
    syncer.sync()


    #Si può automatizzare senza input utente usando direttamente le righe sotto

    #syncer = FolderSynchronizer(source_folder, destination_folder, workers=4, use_hash=False)
    #syncer.sync()