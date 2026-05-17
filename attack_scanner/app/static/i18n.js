(function () {
  const STORAGE_KEY = "attackScanner.language";
  const SUPPORTED = ["en-US", "en-AU", "fr", "es", "pt"];
  const LANGUAGE_NAMES = {
    "en-US": "English (US)",
    "en-AU": "English (Australia)",
    fr: "Francais",
    es: "Espanol",
    pt: "Portugues",
  };

  const translations = {
    "en-AU": {
      "Browser default": "Browser default",
      Language: "Language",
      "English (US)": "English (US)",
      "English (Australia)": "English (Australia)",
      Dashboard: "Dashboard",
      Players: "Players",
      Stats: "Stats",
      Analytics: "Analytics",
      Alliances: "Alliances",
      Add: "Add",
      Docs: "Docs",
      "Manual Add": "Manual Entry",
      Manual: "Manual",
      "Last Assylum: Plague Violation Tracker": "Last Assylum: Plague Violation Tracker",
      "Upload battle report": "Upload battle report",
      "Upload covert ops image": "Upload covert ops image",
      "Upload caravan attack": "Upload caravan attack",
      "Process battle image": "Process battle image",
      "Process ops image": "Process ops image",
      "Process caravan image": "Process caravan image",
      "Server ID filter": "Server ID filter",
      "Attack types over time": "Attack types over time",
      "Daily attack volume by type, filtered by attacking alliance or attacking player.": "Daily attack volume by type, filtered by attacking alliance or attacking player.",
      "All alliances": "All alliances",
      "All attackers": "All attackers",
      "No attacking alliances found": "No attacking alliances found",
      "No attackers found": "No attackers found",
      Reset: "Reset",
      Caravan: "Caravan",
      "No attack data matches these filters.": "No attack data matches these filters.",
      "No defender parsed": "No defender parsed",
      "No submitted image is available for this record.": "No submitted image is available for this record.",
    },
    fr: {
      "Browser default": "Langue du navigateur",
      Language: "Langue",
      "English (US)": "Anglais (Etats-Unis)",
      "English (Australia)": "Anglais (Australie)",
      Francais: "Francais",
      Espanol: "Espagnol",
      Portugues: "Portugais",
      Dashboard: "Tableau de bord",
      Players: "Joueurs",
      Stats: "Stats",
      Analytics: "Analytique",
      Alliances: "Alliances",
      Add: "Ajouter",
      Docs: "Docs",
      "Manual Add": "Ajout manuel",
      Manual: "Manuel",
      "Last Assylum: Plague Violation Tracker": "Last Assylum : suivi des violations de peste",
      "Quarantine ledger": "Registre de quarantaine",
      "Upload battle report": "Importer un rapport de bataille",
      "Upload covert ops image": "Importer une image d'operations secretes",
      "Upload caravan attack": "Importer une attaque de caravane",
      Image: "Image",
      "Server ID": "ID du serveur",
      "Default year": "Annee par defaut",
      "Victim alliance": "Alliance victime",
      "Process battle image": "Traiter l'image de bataille",
      "Process ops image": "Traiter l'image d'operations",
      "Process caravan image": "Traiter l'image de caravane",
      "Recent attacks": "Attaques recentes",
      ID: "ID",
      Attack: "Attaque",
      Type: "Type",
      Attacker: "Attaquant",
      Defender: "Defenseur",
      Server: "Serveur",
      When: "Quand",
      Delete: "Supprimer",
      Source: "Source",
      "Submitted image": "Image soumise",
      "Delete record": "Supprimer l'enregistrement",
      Notes: "Notes",
      Apply: "Appliquer",
      Alliance: "Alliance",
      Attacks: "Attaques",
      Attackers: "Attaquants",
      Targets: "Cibles",
      "Who they attack": "Qui ils attaquent",
      "Who attacks them": "Qui les attaque",
      Enemies: "Ennemis",
      "Members Hit": "Membres touches",
      "Members seen in reports": "Membres vus dans les rapports",
      Name: "Nom",
      "Attacks Made": "Attaques faites",
      "Attacks Received": "Attaques recues",
      Total: "Total",
      "Recent alliance activity": "Activite recente de l'alliance",
      Role: "Role",
      "Alliance activity": "Activite des alliances",
      "Alliance ledger": "Registre des alliances",
      "Attacking Members": "Membres attaquants",
      "Total Activity": "Activite totale",
      "Alliance vs alliance": "Alliance contre alliance",
      "Add attack manually": "Ajouter une attaque manuellement",
      "Attacker name": "Nom de l'attaquant",
      "Attacker alliance tag": "Tag d'alliance attaquante",
      "Defender name": "Nom du defenseur",
      "Defender alliance tag": "Tag d'alliance defenseur",
      "Date/time text": "Texte date/heure",
      Save: "Enregistrer",
      "Search players": "Rechercher des joueurs",
      "Search by name": "Rechercher par nom",
      Search: "Rechercher",
      "Total Events": "Evenements totaux",
      "Attack history": "Historique des attaques",
      "Other party": "Autre partie",
      "Server stats": "Stats du serveur",
      "Attack types over time": "Types d'attaques dans le temps",
      "Daily attack volume by type, filtered by attacking alliance or attacking player.": "Volume quotidien par type, filtre par alliance attaquante ou joueur attaquant.",
      "All alliances": "Toutes les alliances",
      "All attackers": "Tous les attaquants",
      "No attacking alliances found": "Aucune alliance attaquante trouvee",
      "No attackers found": "Aucun attaquant trouve",
      Reset: "Reinitialiser",
      Caravan: "Caravane",
      Battle: "Bataille",
      Ops: "Ops",
      "No attack data matches these filters.": "Aucune donnee d'attaque ne correspond a ces filtres.",
      "Most aggressive alliance": "Alliance la plus agressive",
      "Most attacked alliance": "Alliance la plus attaquee",
      "No attack data yet": "Aucune donnee d'attaque pour l'instant",
      "No defender alliance data yet": "Aucune donnee d'alliance defenseur pour l'instant",
      "Top 10 attackers": "Top 10 des attaquants",
      Battle: "Bataille",
      Ops: "Ops",
      "Top attacking alliances": "Principales alliances attaquantes",
      "Unique Attackers": "Attaquants uniques",
      "Total Attacks": "Total des attaques",
      "Most attacked alliances": "Alliances les plus attaquees",
      "Enemy Alliances": "Alliances ennemies",
      "Top alliance matchups": "Principaux affrontements d'alliances",
      "Deleted records": "Enregistrements supprimes",
      Password: "Mot de passe",
      Review: "Examiner",
      "Deleted attack log": "Journal des attaques supprimees",
      Deleted: "Supprime",
      "Original time": "Heure originale",
      "View image": "Voir l'image",
      "Server 78 alliances": "Alliances du serveur 78",
      Manage: "Gerer",
      Add: "Ajouter",
      Status: "Statut",
      Remove: "Retirer",
      "Managed alliance list": "Liste des alliances gerees",
      "Field manual": "Manuel de terrain",
      "User Manual": "Manuel utilisateur",
      "Daily workflow": "Flux de travail quotidien",
      Uploads: "Imports",
      "Manual records": "Enregistrements manuels",
      "Deletes and retention": "Suppressions et retention",
      "Discord bot": "Bot Discord",
      "Discord scans": "Analyses Discord",
      "Discord queries": "Requetes Discord",
      "Discord troubleshooting": "Depannage Discord",
      "No defender parsed": "Aucun defenseur analyse",
      "No submitted image is available for this record.": "Aucune image soumise n'est disponible pour cet enregistrement.",
      "Enter delete password": "Entrez le mot de passe de suppression",
      "Delete this attack?": "Supprimer cette attaque ?",
      "Remove this alliance from the server 78 list?": "Retirer cette alliance de la liste du serveur 78 ?",
    },
    es: {
      "Browser default": "Idioma del navegador",
      Language: "Idioma",
      "English (US)": "Ingles (EE. UU.)",
      "English (Australia)": "Ingles (Australia)",
      Francais: "Frances",
      Espanol: "Espanol",
      Portugues: "Portugues",
      Dashboard: "Panel",
      Players: "Jugadores",
      Stats: "Estadisticas",
      Analytics: "Analitica",
      Alliances: "Alianzas",
      Add: "Agregar",
      Docs: "Docs",
      "Manual Add": "Alta manual",
      Manual: "Manual",
      "Last Assylum: Plague Violation Tracker": "Last Assylum: rastreador de violaciones de plaga",
      "Quarantine ledger": "Registro de cuarentena",
      "Upload battle report": "Subir informe de batalla",
      "Upload covert ops image": "Subir imagen de operaciones encubiertas",
      "Upload caravan attack": "Subir ataque de caravana",
      Image: "Imagen",
      "Server ID": "ID del servidor",
      "Default year": "Ano predeterminado",
      "Victim alliance": "Alianza victima",
      "Process battle image": "Procesar imagen de batalla",
      "Process ops image": "Procesar imagen de operaciones",
      "Process caravan image": "Procesar imagen de caravana",
      "Recent attacks": "Ataques recientes",
      ID: "ID",
      Attack: "Ataque",
      Type: "Tipo",
      Attacker: "Atacante",
      Defender: "Defensor",
      Server: "Servidor",
      When: "Cuando",
      Delete: "Eliminar",
      Source: "Fuente",
      "Submitted image": "Imagen enviada",
      "Delete record": "Eliminar registro",
      Notes: "Notas",
      Apply: "Aplicar",
      Alliance: "Alianza",
      Attacks: "Ataques",
      Attackers: "Atacantes",
      Targets: "Objetivos",
      "Who they attack": "A quienes atacan",
      "Who attacks them": "Quienes los atacan",
      Enemies: "Enemigos",
      "Members Hit": "Miembros golpeados",
      "Members seen in reports": "Miembros vistos en informes",
      Name: "Nombre",
      "Attacks Made": "Ataques realizados",
      "Attacks Received": "Ataques recibidos",
      Total: "Total",
      "Recent alliance activity": "Actividad reciente de la alianza",
      Role: "Rol",
      "Alliance activity": "Actividad de alianzas",
      "Alliance ledger": "Registro de alianzas",
      "Attacking Members": "Miembros atacantes",
      "Total Activity": "Actividad total",
      "Alliance vs alliance": "Alianza contra alianza",
      "Add attack manually": "Agregar ataque manualmente",
      "Attacker name": "Nombre del atacante",
      "Attacker alliance tag": "Etiqueta de alianza atacante",
      "Defender name": "Nombre del defensor",
      "Defender alliance tag": "Etiqueta de alianza defensora",
      "Date/time text": "Texto de fecha/hora",
      Save: "Guardar",
      "Search players": "Buscar jugadores",
      "Search by name": "Buscar por nombre",
      Search: "Buscar",
      "Total Events": "Eventos totales",
      "Attack history": "Historial de ataques",
      "Other party": "Otra parte",
      "Server stats": "Estadisticas del servidor",
      "Attack types over time": "Tipos de ataque en el tiempo",
      "Daily attack volume by type, filtered by attacking alliance or attacking player.": "Volumen diario por tipo, filtrado por alianza atacante o jugador atacante.",
      "All alliances": "Todas las alianzas",
      "All attackers": "Todos los atacantes",
      "No attacking alliances found": "No se encontraron alianzas atacantes",
      "No attackers found": "No se encontraron atacantes",
      Reset: "Restablecer",
      Caravan: "Caravana",
      Battle: "Batalla",
      Ops: "Ops",
      "No attack data matches these filters.": "Ningun dato de ataque coincide con estos filtros.",
      "Most aggressive alliance": "Alianza mas agresiva",
      "Most attacked alliance": "Alianza mas atacada",
      "No attack data yet": "Aun no hay datos de ataques",
      "No defender alliance data yet": "Aun no hay datos de alianza defensora",
      "Top 10 attackers": "10 principales atacantes",
      Battle: "Batalla",
      Ops: "Ops",
      "Top attacking alliances": "Principales alianzas atacantes",
      "Unique Attackers": "Atacantes unicos",
      "Total Attacks": "Ataques totales",
      "Most attacked alliances": "Alianzas mas atacadas",
      "Enemy Alliances": "Alianzas enemigas",
      "Top alliance matchups": "Principales enfrentamientos de alianzas",
      "Deleted records": "Registros eliminados",
      Password: "Contrasena",
      Review: "Revisar",
      "Deleted attack log": "Registro de ataques eliminados",
      Deleted: "Eliminado",
      "Original time": "Hora original",
      "View image": "Ver imagen",
      "Server 78 alliances": "Alianzas del servidor 78",
      Manage: "Gestionar",
      Add: "Agregar",
      Status: "Estado",
      Remove: "Quitar",
      "Managed alliance list": "Lista de alianzas gestionadas",
      "Field manual": "Manual de campo",
      "User Manual": "Manual de usuario",
      "Daily workflow": "Flujo diario",
      Uploads: "Subidas",
      "Manual records": "Registros manuales",
      "Deletes and retention": "Eliminaciones y retencion",
      "Discord bot": "Bot de Discord",
      "Discord scans": "Escaneos de Discord",
      "Discord queries": "Consultas de Discord",
      "Discord troubleshooting": "Solucion de problemas de Discord",
      "No defender parsed": "No se analizo ningun defensor",
      "No submitted image is available for this record.": "No hay imagen enviada disponible para este registro.",
      "Enter delete password": "Introduce la contrasena de eliminacion",
      "Delete this attack?": "Eliminar este ataque?",
      "Remove this alliance from the server 78 list?": "Quitar esta alianza de la lista del servidor 78?",
    },
    pt: {
      "Browser default": "Idioma do navegador",
      Language: "Idioma",
      "English (US)": "Ingles (EUA)",
      "English (Australia)": "Ingles (Australia)",
      Francais: "Frances",
      Espanol: "Espanhol",
      Portugues: "Portugues",
      Dashboard: "Painel",
      Players: "Jogadores",
      Stats: "Estatisticas",
      Analytics: "Analises",
      Alliances: "Aliancas",
      Add: "Adicionar",
      Docs: "Docs",
      "Manual Add": "Adicionar manualmente",
      Manual: "Manual",
      "Last Assylum: Plague Violation Tracker": "Last Assylum: rastreador de violacoes da praga",
      "Quarantine ledger": "Registro de quarentena",
      "Upload battle report": "Enviar relatorio de batalha",
      "Upload covert ops image": "Enviar imagem de operacoes secretas",
      "Upload caravan attack": "Enviar ataque de caravana",
      Image: "Imagem",
      "Server ID": "ID do servidor",
      "Default year": "Ano padrao",
      "Victim alliance": "Alianca vitima",
      "Process battle image": "Processar imagem de batalha",
      "Process ops image": "Processar imagem de operacoes",
      "Process caravan image": "Processar imagem de caravana",
      "Recent attacks": "Ataques recentes",
      ID: "ID",
      Attack: "Ataque",
      Type: "Tipo",
      Attacker: "Atacante",
      Defender: "Defensor",
      Server: "Servidor",
      When: "Quando",
      Delete: "Excluir",
      Source: "Origem",
      "Submitted image": "Imagem enviada",
      "Delete record": "Excluir registro",
      Notes: "Notas",
      Apply: "Aplicar",
      Alliance: "Alianca",
      Attacks: "Ataques",
      Attackers: "Atacantes",
      Targets: "Alvos",
      "Who they attack": "Quem eles atacam",
      "Who attacks them": "Quem os ataca",
      Enemies: "Inimigos",
      "Members Hit": "Membros atingidos",
      "Members seen in reports": "Membros vistos nos relatorios",
      Name: "Nome",
      "Attacks Made": "Ataques feitos",
      "Attacks Received": "Ataques recebidos",
      Total: "Total",
      "Recent alliance activity": "Atividade recente da alianca",
      Role: "Funcao",
      "Alliance activity": "Atividade das aliancas",
      "Alliance ledger": "Registro das aliancas",
      "Attacking Members": "Membros atacantes",
      "Total Activity": "Atividade total",
      "Alliance vs alliance": "Alianca contra alianca",
      "Add attack manually": "Adicionar ataque manualmente",
      "Attacker name": "Nome do atacante",
      "Attacker alliance tag": "Tag da alianca atacante",
      "Defender name": "Nome do defensor",
      "Defender alliance tag": "Tag da alianca defensora",
      "Date/time text": "Texto de data/hora",
      Save: "Salvar",
      "Search players": "Pesquisar jogadores",
      "Search by name": "Pesquisar por nome",
      Search: "Pesquisar",
      "Total Events": "Eventos totais",
      "Attack history": "Historico de ataques",
      "Other party": "Outra parte",
      "Server stats": "Estatisticas do servidor",
      "Attack types over time": "Tipos de ataque ao longo do tempo",
      "Daily attack volume by type, filtered by attacking alliance or attacking player.": "Volume diario por tipo, filtrado por alianca atacante ou jogador atacante.",
      "All alliances": "Todas as aliancas",
      "All attackers": "Todos os atacantes",
      "No attacking alliances found": "Nenhuma alianca atacante encontrada",
      "No attackers found": "Nenhum atacante encontrado",
      Reset: "Redefinir",
      Caravan: "Caravana",
      Battle: "Batalha",
      Ops: "Ops",
      "No attack data matches these filters.": "Nenhum dado de ataque corresponde a estes filtros.",
      "Most aggressive alliance": "Alianca mais agressiva",
      "Most attacked alliance": "Alianca mais atacada",
      "No attack data yet": "Ainda nao ha dados de ataques",
      "No defender alliance data yet": "Ainda nao ha dados de alianca defensora",
      "Top 10 attackers": "10 principais atacantes",
      Battle: "Batalha",
      Ops: "Ops",
      "Top attacking alliances": "Principais aliancas atacantes",
      "Unique Attackers": "Atacantes unicos",
      "Total Attacks": "Ataques totais",
      "Most attacked alliances": "Aliancas mais atacadas",
      "Enemy Alliances": "Aliancas inimigas",
      "Top alliance matchups": "Principais confrontos de aliancas",
      "Deleted records": "Registros excluidos",
      Password: "Senha",
      Review: "Revisar",
      "Deleted attack log": "Log de ataques excluidos",
      Deleted: "Excluido",
      "Original time": "Hora original",
      "View image": "Ver imagem",
      "Server 78 alliances": "Aliancas do servidor 78",
      Manage: "Gerenciar",
      Add: "Adicionar",
      Status: "Status",
      Remove: "Remover",
      "Managed alliance list": "Lista de aliancas gerenciadas",
      "Field manual": "Manual de campo",
      "User Manual": "Manual do usuario",
      "Daily workflow": "Fluxo diario",
      Uploads: "Envios",
      "Manual records": "Registros manuais",
      "Deletes and retention": "Exclusoes e retencao",
      "Discord bot": "Bot do Discord",
      "Discord scans": "Escaneamentos do Discord",
      "Discord queries": "Consultas do Discord",
      "Discord troubleshooting": "Solucao de problemas do Discord",
      "No defender parsed": "Nenhum defensor analisado",
      "No submitted image is available for this record.": "Nenhuma imagem enviada esta disponivel para este registro.",
      "Enter delete password": "Digite a senha de exclusao",
      "Delete this attack?": "Excluir este ataque?",
      "Remove this alliance from the server 78 list?": "Remover esta alianca da lista do servidor 78?",
    },
  };

  const manualTranslations = {
    fr: {
      "Use the dashboard to upload a battle report, covert ops screenshot, or caravan attack screenshot.": "Utilisez le tableau de bord pour importer un rapport de bataille, une capture d'operations secretes ou une capture d'attaque de caravane.",
      "Leave server ID blank to use the parser result, or enter the server manually.": "Laissez l'ID du serveur vide pour utiliser le resultat de l'analyseur, ou saisissez le serveur manuellement.",
      "The default year is the current calendar year and helps when screenshots only show month and day.": "L'annee par defaut est l'annee civile actuelle et aide quand les captures ne montrent que le mois et le jour.",
      "Review parsed records in Recent attacks, Players, Stats, and Alliances.": "Consultez les enregistrements analyses dans Attaques recentes, Joueurs, Stats et Alliances.",
      "Battle reports track attacker, defender, alliances, server, and event time.": "Les rapports de bataille suivent l'attaquant, le defenseur, les alliances, le serveur et l'heure de l'evenement.",
      "The same image cannot be submitted twice while it is active.": "La meme image ne peut pas etre soumise deux fois tant qu'elle est active.",
      "Click a record ID to view the submitted image and parsed details.": "Cliquez sur l'ID d'un enregistrement pour voir l'image soumise et les details analyses.",
      "Covert ops reports track the red attacker entries from the report image.": "Les rapports d'operations secretes suivent les entrees rouges d'attaquants dans l'image du rapport.",
      "For covert ops uploads, optionally enter a victim alliance so ops events count against that alliance in stats.": "Pour les imports d'operations secretes, saisissez eventuellement une alliance victime afin que les evenements comptent contre cette alliance dans les stats.",
      "Caravan attack reports track the top caravan owner as the victim and the dated battle-history entries as attackers.": "Les rapports d'attaque de caravane utilisent le proprietaire principal comme victime et les entrees datees d'historique de bataille comme attaquants.",
      "Caravan names can be in English, Spanish, Cyrillic, or other OCR-readable scripts.": "Les noms de caravane peuvent etre en anglais, espagnol, cyrillique ou autres ecritures lisibles par OCR.",
      "Non-English parsing works best when the matching Tesseract language pack is installed on the server.": "L'analyse non anglaise fonctionne mieux lorsque le pack de langue Tesseract correspondant est installe sur le serveur.",
      "Manual records are added from": "Les enregistrements manuels sont ajoutes depuis",
      "An image is required even when entering record details by hand.": "Une image est requise meme si les details sont saisis a la main.",
      "Alliance tags come from the portion of the player name inside brackets.": "Les tags d'alliance viennent de la partie du nom du joueur entre crochets.",
      "Example:": "Exemple :",
      "records alliance": "enregistre l'alliance",
      "The": "La page",
      "page shows attack volume, attacks received, member activity, and matchups.": "affiche le volume d'attaques, les attaques recues, l'activite des membres et les affrontements.",
      "Managed Server 78 alliances display green.": "Les alliances gerees du serveur 78 s'affichent en vert.",
      "Other alliances display red.": "Les autres alliances s'affichent en rouge.",
      "Manage the hidden Server 78 alliance list at": "Gerez la liste cachee des alliances du serveur 78 a",
      "Deleting a record asks for the moderator password.": "La suppression d'un enregistrement demande le mot de passe du moderateur.",
      "The current delete password is": "Le mot de passe de suppression actuel est",
      "Deleted records are soft-deleted, so the database row and image are retained.": "Les enregistrements supprimes sont masques logiquement, donc la ligne de base de donnees et l'image sont conservees.",
      "Records older than 30 days are automatically soft-deleted on app startup.": "Les enregistrements de plus de 30 jours sont automatiquement masques au demarrage de l'application.",
      "Review deleted records at": "Consultez les enregistrements supprimes a",
      "Invite the bot to your Discord server from the Discord Developer Portal using the application's OAuth2 bot invite URL.": "Invitez le bot sur votre serveur Discord depuis le portail developpeur Discord avec l'URL d'invitation OAuth2 de l'application.",
      "Enable Message Content Intent for the bot in the Discord Developer Portal.": "Activez Message Content Intent pour le bot dans le portail developpeur Discord.",
      "Start the bot with": "Demarrez le bot avec",
      "set to the bot token, not the application ID or public key.": "defini sur le jeton du bot, pas sur l'ID d'application ni la cle publique.",
      "if most scans should default to Server 78.": "si la plupart des analyses doivent utiliser le serveur 78 par defaut.",
      "Use": "Utilisez",
      "to check whether the bot is online. It should reply with": "pour verifier si le bot est en ligne. Il doit repondre",
      "Mention the bot and attach one or more screenshots.": "Mentionnez le bot et joignez une ou plusieurs captures.",
      "to process the image as a battle report.": "pour traiter l'image comme un rapport de bataille.",
      "to process the image as a covert ops report.": "pour traiter l'image comme un rapport d'operations secretes.",
      "to process the image as a caravan attack report.": "pour traiter l'image comme un rapport d'attaque de caravane.",
      "with a battle screenshot attached.": "avec une capture de bataille jointe.",
      "with a covert ops screenshot attached.": "avec une capture d'operations secretes jointe.",
      "with a caravan attack screenshot attached.": "avec une capture d'attaque de caravane jointe.",
      "For ops scans, the victim alliance can be written as": "Pour les analyses d'operations, l'alliance victime peut etre ecrite",
      "or": "ou",
      "If no parser type is included, the bot tries to auto-detect the screenshot type.": "Si aucun type d'analyseur n'est indique, le bot essaie de detecter automatiquement le type de capture.",
      "Duplicate images are rejected the same way they are in the web dashboard.": "Les images en doublon sont rejetees comme dans le tableau de bord web.",
      "to show top attackers, top attacking alliances, and most attacked alliances.": "pour afficher les meilleurs attaquants, les principales alliances attaquantes et les alliances les plus attaquees.",
      "to show recent records.": "pour afficher les enregistrements recents.",
      "to show a player's recent attack history.": "pour afficher l'historique recent des attaques d'un joueur.",
      "to show Discord image scan options.": "pour afficher les options d'analyse d'image Discord.",
      "to filter commands to a specific server.": "pour filtrer les commandes sur un serveur specifique.",
      "to recent/history commands to control how many rows are shown.": "aux commandes recent/history pour controler le nombre de lignes affichees.",
      "The dashboard alias also works:": "L'alias du tableau de bord fonctionne aussi :",
      "does not respond, make sure the bot process is running.": "ne repond pas, verifiez que le processus du bot fonctionne.",
      "If mention commands do not work, confirm Message Content Intent is enabled.": "Si les commandes par mention ne fonctionnent pas, confirmez que Message Content Intent est active.",
      "If the bot cannot reply, check channel permissions for view channel, read message history, and send messages.": "Si le bot ne peut pas repondre, verifiez les permissions du salon pour voir le salon, lire l'historique et envoyer des messages.",
      "If web records and Discord records do not match, make sure both are using the same SQLite database path.": "Si les enregistrements web et Discord ne correspondent pas, assurez-vous qu'ils utilisent le meme chemin de base SQLite.",
      "For public Discord interactions webhooks, Discord requires an HTTPS interactions URL.": "Pour les webhooks publics d'interactions Discord, Discord exige une URL HTTPS.",
      "These records are hidden from normal dashboards and stats. Images remain stored, but their upload hashes were released when the record was deleted.": "Ces enregistrements sont masques des tableaux de bord et stats normaux. Les images restent stockees, mais leurs hachages d'import ont ete liberes lors de la suppression.",
      "Alliances on this list render green. Any alliance not listed renders red.": "Les alliances de cette liste s'affichent en vert. Toute alliance absente s'affiche en rouge.",
      "Alliance tag, for example AVL": "Tag d'alliance, par exemple AVL",
    },
    es: {
      "Use the dashboard to upload a battle report, covert ops screenshot, or caravan attack screenshot.": "Usa el panel para subir un informe de batalla, una captura de operaciones encubiertas o una captura de ataque de caravana.",
      "Leave server ID blank to use the parser result, or enter the server manually.": "Deja el ID del servidor en blanco para usar el resultado del analizador, o introduce el servidor manualmente.",
      "The default year is the current calendar year and helps when screenshots only show month and day.": "El ano predeterminado es el ano calendario actual y ayuda cuando las capturas solo muestran mes y dia.",
      "Review parsed records in Recent attacks, Players, Stats, and Alliances.": "Revisa los registros analizados en Ataques recientes, Jugadores, Estadisticas y Alianzas.",
      "Battle reports track attacker, defender, alliances, server, and event time.": "Los informes de batalla registran atacante, defensor, alianzas, servidor y hora del evento.",
      "The same image cannot be submitted twice while it is active.": "La misma imagen no se puede enviar dos veces mientras esta activa.",
      "Click a record ID to view the submitted image and parsed details.": "Haz clic en un ID de registro para ver la imagen enviada y los detalles analizados.",
      "Covert ops reports track the red attacker entries from the report image.": "Los informes de operaciones encubiertas registran las entradas rojas de atacantes en la imagen del informe.",
      "For covert ops uploads, optionally enter a victim alliance so ops events count against that alliance in stats.": "Para subidas de operaciones encubiertas, puedes introducir una alianza victima para que esos eventos cuenten contra esa alianza en estadisticas.",
      "Caravan attack reports track the top caravan owner as the victim and the dated battle-history entries as attackers.": "Los informes de ataque de caravana usan al propietario superior como victima y las entradas fechadas del historial de batalla como atacantes.",
      "Caravan names can be in English, Spanish, Cyrillic, or other OCR-readable scripts.": "Los nombres de caravana pueden estar en ingles, espanol, cirilico u otras escrituras legibles por OCR.",
      "Non-English parsing works best when the matching Tesseract language pack is installed on the server.": "El analisis no ingles funciona mejor cuando el paquete de idioma de Tesseract correspondiente esta instalado en el servidor.",
      "Manual records are added from": "Los registros manuales se agregan desde",
      "An image is required even when entering record details by hand.": "Se requiere una imagen incluso al introducir los detalles a mano.",
      "Alliance tags come from the portion of the player name inside brackets.": "Las etiquetas de alianza vienen de la parte del nombre del jugador entre corchetes.",
      "Example:": "Ejemplo:",
      "records alliance": "registra la alianza",
      "The": "La pagina",
      "page shows attack volume, attacks received, member activity, and matchups.": "muestra volumen de ataques, ataques recibidos, actividad de miembros y enfrentamientos.",
      "Managed Server 78 alliances display green.": "Las alianzas gestionadas del servidor 78 se muestran en verde.",
      "Other alliances display red.": "Las demas alianzas se muestran en rojo.",
      "Manage the hidden Server 78 alliance list at": "Gestiona la lista oculta de alianzas del servidor 78 en",
      "Deleting a record asks for the moderator password.": "Eliminar un registro solicita la contrasena del moderador.",
      "The current delete password is": "La contrasena de eliminacion actual es",
      "Deleted records are soft-deleted, so the database row and image are retained.": "Los registros eliminados se borran logicamente, por lo que se conservan la fila de base de datos y la imagen.",
      "Records older than 30 days are automatically soft-deleted on app startup.": "Los registros con mas de 30 dias se borran logicamente al iniciar la app.",
      "Review deleted records at": "Revisa los registros eliminados en",
      "Invite the bot to your Discord server from the Discord Developer Portal using the application's OAuth2 bot invite URL.": "Invita el bot a tu servidor Discord desde el Portal de Desarrolladores usando la URL de invitacion OAuth2 de la aplicacion.",
      "Enable Message Content Intent for the bot in the Discord Developer Portal.": "Activa Message Content Intent para el bot en el Portal de Desarrolladores de Discord.",
      "Start the bot with": "Inicia el bot con",
      "set to the bot token, not the application ID or public key.": "configurado con el token del bot, no con el ID de aplicacion ni la clave publica.",
      "if most scans should default to Server 78.": "si la mayoria de escaneos deben usar el servidor 78 por defecto.",
      "Use": "Usa",
      "to check whether the bot is online. It should reply with": "para comprobar si el bot esta en linea. Deberia responder",
      "Mention the bot and attach one or more screenshots.": "Menciona al bot y adjunta una o mas capturas.",
      "to process the image as a battle report.": "para procesar la imagen como informe de batalla.",
      "to process the image as a covert ops report.": "para procesar la imagen como informe de operaciones encubiertas.",
      "to process the image as a caravan attack report.": "para procesar la imagen como informe de ataque de caravana.",
      "with a battle screenshot attached.": "con una captura de batalla adjunta.",
      "with a covert ops screenshot attached.": "con una captura de operaciones encubiertas adjunta.",
      "with a caravan attack screenshot attached.": "con una captura de ataque de caravana adjunta.",
      "For ops scans, the victim alliance can be written as": "Para escaneos de operaciones, la alianza victima puede escribirse como",
      "or": "o",
      "If no parser type is included, the bot tries to auto-detect the screenshot type.": "Si no se incluye tipo de analizador, el bot intenta detectar automaticamente el tipo de captura.",
      "Duplicate images are rejected the same way they are in the web dashboard.": "Las imagenes duplicadas se rechazan igual que en el panel web.",
      "to show top attackers, top attacking alliances, and most attacked alliances.": "para mostrar principales atacantes, principales alianzas atacantes y alianzas mas atacadas.",
      "to show recent records.": "para mostrar registros recientes.",
      "to show a player's recent attack history.": "para mostrar el historial reciente de ataques de un jugador.",
      "to show Discord image scan options.": "para mostrar opciones de escaneo de imagen en Discord.",
      "to filter commands to a specific server.": "para filtrar comandos a un servidor especifico.",
      "to recent/history commands to control how many rows are shown.": "a comandos recent/history para controlar cuantas filas se muestran.",
      "The dashboard alias also works:": "El alias del panel tambien funciona:",
      "does not respond, make sure the bot process is running.": "no responde, asegurate de que el proceso del bot se este ejecutando.",
      "If mention commands do not work, confirm Message Content Intent is enabled.": "Si los comandos por mencion no funcionan, confirma que Message Content Intent este activado.",
      "If the bot cannot reply, check channel permissions for view channel, read message history, and send messages.": "Si el bot no puede responder, revisa permisos del canal para ver canal, leer historial y enviar mensajes.",
      "If web records and Discord records do not match, make sure both are using the same SQLite database path.": "Si los registros web y de Discord no coinciden, asegurate de que ambos usen la misma ruta SQLite.",
      "For public Discord interactions webhooks, Discord requires an HTTPS interactions URL.": "Para webhooks publicos de interacciones de Discord, Discord requiere una URL HTTPS.",
      "These records are hidden from normal dashboards and stats. Images remain stored, but their upload hashes were released when the record was deleted.": "Estos registros se ocultan de paneles y estadisticas normales. Las imagenes siguen guardadas, pero sus hashes de subida se liberaron al eliminar el registro.",
      "Alliances on this list render green. Any alliance not listed renders red.": "Las alianzas de esta lista se muestran en verde. Cualquier alianza ausente se muestra en rojo.",
      "Alliance tag, for example AVL": "Etiqueta de alianza, por ejemplo AVL",
    },
    pt: {
      "Use the dashboard to upload a battle report, covert ops screenshot, or caravan attack screenshot.": "Use o painel para enviar um relatorio de batalha, captura de operacoes secretas ou captura de ataque de caravana.",
      "Leave server ID blank to use the parser result, or enter the server manually.": "Deixe o ID do servidor em branco para usar o resultado do analisador, ou informe o servidor manualmente.",
      "The default year is the current calendar year and helps when screenshots only show month and day.": "O ano padrao e o ano civil atual e ajuda quando as capturas mostram apenas mes e dia.",
      "Review parsed records in Recent attacks, Players, Stats, and Alliances.": "Revise os registros analisados em Ataques recentes, Jogadores, Estatisticas e Aliancas.",
      "Battle reports track attacker, defender, alliances, server, and event time.": "Relatorios de batalha registram atacante, defensor, aliancas, servidor e horario do evento.",
      "The same image cannot be submitted twice while it is active.": "A mesma imagem nao pode ser enviada duas vezes enquanto esta ativa.",
      "Click a record ID to view the submitted image and parsed details.": "Clique no ID de um registro para ver a imagem enviada e os detalhes analisados.",
      "Covert ops reports track the red attacker entries from the report image.": "Relatorios de operacoes secretas registram as entradas vermelhas de atacantes na imagem do relatorio.",
      "For covert ops uploads, optionally enter a victim alliance so ops events count against that alliance in stats.": "Para envios de operacoes secretas, informe opcionalmente uma alianca vitima para que os eventos contem contra essa alianca nas estatisticas.",
      "Caravan attack reports track the top caravan owner as the victim and the dated battle-history entries as attackers.": "Relatorios de ataque de caravana usam o proprietario principal como vitima e as entradas datadas do historico de batalha como atacantes.",
      "Caravan names can be in English, Spanish, Cyrillic, or other OCR-readable scripts.": "Nomes de caravana podem estar em ingles, espanhol, cirilico ou outras escritas legiveis por OCR.",
      "Non-English parsing works best when the matching Tesseract language pack is installed on the server.": "A analise nao inglesa funciona melhor quando o pacote de idioma Tesseract correspondente esta instalado no servidor.",
      "Manual records are added from": "Registros manuais sao adicionados em",
      "An image is required even when entering record details by hand.": "Uma imagem e obrigatoria mesmo ao inserir detalhes manualmente.",
      "Alliance tags come from the portion of the player name inside brackets.": "Tags de alianca vem da parte do nome do jogador entre colchetes.",
      "Example:": "Exemplo:",
      "records alliance": "registra a alianca",
      "The": "A pagina",
      "page shows attack volume, attacks received, member activity, and matchups.": "mostra volume de ataques, ataques recebidos, atividade de membros e confrontos.",
      "Managed Server 78 alliances display green.": "Aliancas gerenciadas do servidor 78 aparecem em verde.",
      "Other alliances display red.": "Outras aliancas aparecem em vermelho.",
      "Manage the hidden Server 78 alliance list at": "Gerencie a lista oculta de aliancas do servidor 78 em",
      "Deleting a record asks for the moderator password.": "Excluir um registro solicita a senha do moderador.",
      "The current delete password is": "A senha de exclusao atual e",
      "Deleted records are soft-deleted, so the database row and image are retained.": "Registros excluidos sao removidos logicamente, entao a linha do banco de dados e a imagem sao mantidas.",
      "Records older than 30 days are automatically soft-deleted on app startup.": "Registros com mais de 30 dias sao removidos logicamente ao iniciar o app.",
      "Review deleted records at": "Revise registros excluidos em",
      "Invite the bot to your Discord server from the Discord Developer Portal using the application's OAuth2 bot invite URL.": "Convide o bot para seu servidor Discord pelo Portal de Desenvolvedores usando a URL OAuth2 de convite do aplicativo.",
      "Enable Message Content Intent for the bot in the Discord Developer Portal.": "Ative Message Content Intent para o bot no Portal de Desenvolvedores do Discord.",
      "Start the bot with": "Inicie o bot com",
      "set to the bot token, not the application ID or public key.": "definido como o token do bot, nao o ID do aplicativo nem a chave publica.",
      "if most scans should default to Server 78.": "se a maioria dos escaneamentos deve usar o servidor 78 por padrao.",
      "Use": "Use",
      "to check whether the bot is online. It should reply with": "para verificar se o bot esta online. Ele deve responder",
      "Mention the bot and attach one or more screenshots.": "Mencione o bot e anexe uma ou mais capturas.",
      "to process the image as a battle report.": "para processar a imagem como relatorio de batalha.",
      "to process the image as a covert ops report.": "para processar a imagem como relatorio de operacoes secretas.",
      "to process the image as a caravan attack report.": "para processar a imagem como relatorio de ataque de caravana.",
      "with a battle screenshot attached.": "com uma captura de batalha anexada.",
      "with a covert ops screenshot attached.": "com uma captura de operacoes secretas anexada.",
      "with a caravan attack screenshot attached.": "com uma captura de ataque de caravana anexada.",
      "For ops scans, the victim alliance can be written as": "Para escaneamentos de operacoes, a alianca vitima pode ser escrita como",
      "or": "ou",
      "If no parser type is included, the bot tries to auto-detect the screenshot type.": "Se nenhum tipo de analisador for incluido, o bot tenta detectar automaticamente o tipo de captura.",
      "Duplicate images are rejected the same way they are in the web dashboard.": "Imagens duplicadas sao rejeitadas da mesma forma que no painel web.",
      "to show top attackers, top attacking alliances, and most attacked alliances.": "para mostrar principais atacantes, principais aliancas atacantes e aliancas mais atacadas.",
      "to show recent records.": "para mostrar registros recentes.",
      "to show a player's recent attack history.": "para mostrar o historico recente de ataques de um jogador.",
      "to show Discord image scan options.": "para mostrar opcoes de escaneamento de imagem no Discord.",
      "to filter commands to a specific server.": "para filtrar comandos por um servidor especifico.",
      "to recent/history commands to control how many rows are shown.": "a comandos recent/history para controlar quantas linhas sao exibidas.",
      "The dashboard alias also works:": "O alias do painel tambem funciona:",
      "does not respond, make sure the bot process is running.": "nao responde, confirme que o processo do bot esta em execucao.",
      "If mention commands do not work, confirm Message Content Intent is enabled.": "Se comandos por mencao nao funcionarem, confirme que Message Content Intent esta ativado.",
      "If the bot cannot reply, check channel permissions for view channel, read message history, and send messages.": "Se o bot nao puder responder, verifique permissoes do canal para ver canal, ler historico e enviar mensagens.",
      "If web records and Discord records do not match, make sure both are using the same SQLite database path.": "Se registros web e Discord nao coincidirem, confirme que ambos usam o mesmo caminho SQLite.",
      "For public Discord interactions webhooks, Discord requires an HTTPS interactions URL.": "Para webhooks publicos de interacoes Discord, o Discord exige uma URL HTTPS.",
      "These records are hidden from normal dashboards and stats. Images remain stored, but their upload hashes were released when the record was deleted.": "Esses registros ficam ocultos dos paineis e estatisticas normais. As imagens permanecem armazenadas, mas seus hashes de envio foram liberados quando o registro foi excluido.",
      "Alliances on this list render green. Any alliance not listed renders red.": "Aliancas nesta lista aparecem em verde. Qualquer alianca ausente aparece em vermelho.",
      "Alliance tag, for example AVL": "Tag de alianca, por exemplo AVL",
    },
  };

  for (const [lang, values] of Object.entries(manualTranslations)) {
    translations[lang] = Object.assign(translations[lang], values);
  }

  function normalizeLanguage(value) {
    if (!value) {
      return "en-US";
    }
    const tag = value.toLowerCase();
    if (tag === "en-au") {
      return "en-AU";
    }
    if (tag.startsWith("fr")) {
      return "fr";
    }
    if (tag.startsWith("es")) {
      return "es";
    }
    if (tag.startsWith("pt")) {
      return "pt";
    }
    return "en-US";
  }

  function detectLanguage() {
    const languages = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language];
    for (const language of languages) {
      const normalized = normalizeLanguage(language);
      if (SUPPORTED.includes(normalized)) {
        return normalized;
      }
    }
    return "en-US";
  }

  function selectedLanguage() {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved && saved !== "auto" ? normalizeLanguage(saved) : detectLanguage();
  }

  function translateValue(value, lang) {
    const dictionary = translations[lang] || {};
    return dictionary[value] || value;
  }

  function translateText(value, lang) {
    const prefix = value.match(/^\s*/)[0];
    const suffix = value.match(/\s*$/)[0];
    const trimmed = value.trim();
    if (!trimmed) {
      return value;
    }

    const dictionary = translations[lang] || {};
    if (dictionary[trimmed]) {
      return prefix + dictionary[trimmed] + suffix;
    }

    const pageTitle = trimmed.match(/^(.+) - Last Assylum: Plague Violation Tracker$/);
    if (pageTitle) {
      return prefix + translateValue(pageTitle[1], lang) + " - " + translateValue("Last Assylum: Plague Violation Tracker", lang) + suffix;
    }

    const attackTitle = trimmed.match(/^Attack #(.+)$/);
    if (attackTitle && dictionary.Attack) {
      return prefix + dictionary.Attack + " #" + attackTitle[1] + suffix;
    }

    const dynamicPatterns = [
      [/^(\d+) attacks from (\d+) member\(s\)$/, { fr: "$1 attaques par $2 membre(s)", es: "$1 ataques de $2 miembro(s)", pt: "$1 ataques de $2 membro(s)" }],
      [/^(\d+) attacks against (\d+) member\(s\)$/, { fr: "$1 attaques contre $2 membre(s)", es: "$1 ataques contra $2 miembro(s)", pt: "$1 ataques contra $2 membro(s)" }],
      [/^Server: (.+)$/, { fr: "Serveur : $1", es: "Servidor: $1", pt: "Servidor: $1" }],
    ];

    for (const [pattern, replacements] of dynamicPatterns) {
      if (pattern.test(trimmed) && replacements[lang]) {
        return prefix + trimmed.replace(pattern, replacements[lang]) + suffix;
      }
    }

    return value;
  }

  function walkTextNodes(root, callback) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || ["SCRIPT", "STYLE", "TEXTAREA"].includes(parent.tagName)) {
          return NodeFilter.FILTER_REJECT;
        }
        return node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
      },
    });

    const nodes = [];
    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
    }
    nodes.forEach(callback);
  }

  const originalTitle = document.title;

  function rememberOriginal(element, attribute) {
    const key = "data-i18n-original-" + attribute.replace(/[^a-z0-9]/gi, "-").toLowerCase();
    if (!element.hasAttribute(key)) {
      element.setAttribute(key, element.getAttribute(attribute) || "");
    }
    return element.getAttribute(key) || "";
  }

  function applyLanguage(lang) {
    document.documentElement.lang = lang;

    walkTextNodes(document.body, (node) => {
      if (!node.__i18nOriginal) {
        node.__i18nOriginal = node.nodeValue;
      }
      node.nodeValue = translateText(node.__i18nOriginal, lang);
    });

    document.querySelectorAll("[placeholder]").forEach((element) => {
      element.setAttribute("placeholder", translateValue(rememberOriginal(element, "placeholder"), lang));
    });

    document.querySelectorAll("[aria-label]").forEach((element) => {
      element.setAttribute("aria-label", translateValue(rememberOriginal(element, "aria-label"), lang));
    });

    document.querySelectorAll("img[alt]").forEach((element) => {
      element.setAttribute("alt", translateValue(rememberOriginal(element, "alt"), lang));
    });

    document.title = translateText(originalTitle, lang);
  }

  function setupSwitcher() {
    const select = document.getElementById("language-select");
    if (!select) {
      return;
    }
    select.value = localStorage.getItem(STORAGE_KEY) || "auto";
    select.addEventListener("change", () => {
      localStorage.setItem(STORAGE_KEY, select.value);
      applyLanguage(selectedLanguage());
    });
  }

  const nativePrompt = window.prompt.bind(window);
  const nativeConfirm = window.confirm.bind(window);
  window.prompt = function (message, defaultValue) {
    return nativePrompt(translateValue(message, selectedLanguage()), defaultValue);
  };
  window.confirm = function (message) {
    return nativeConfirm(translateValue(message, selectedLanguage()));
  };

  document.addEventListener("DOMContentLoaded", () => {
    setupSwitcher();
    applyLanguage(selectedLanguage());
    window.AttackScannerI18n = {
      apply: applyLanguage,
      detect: detectLanguage,
      language: selectedLanguage,
      names: LANGUAGE_NAMES,
    };
  });
})();
