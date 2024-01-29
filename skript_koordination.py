# Dieses Python-Skript koordiniert den Ablauf aller Skripte.
# Der Workflow wird durch das Starten von "main.py" initiiert, "skript_koordination.py" kann vom User ignoriert werden.

# Autor: Daniel Seisenbacher
# Interpreter: Python 3.9 (arcgispro-py3)
# Datum: 20. Jänner 2024


import workspace_funktionen
import prj_funktionen
import vektor_lokal
import flugstreifen_benennung
import vektor_global
import raster_global
from info_wrapper import *
import arcpy


@func_info
def input_parameter(speicherort, dgm_pfad, mehrere_operate, mehrere_operate_input, stereo_modell_erstellen,
                    meridianstreifen_pfad, externe_prj_sammlung, datenquelle):
    """
    Diese Funktion interpretiert die User-Inputs für den Ablauf.
    Parameter:
        - speicherort (str): Pfad des Speicherorts sämtlicher Ergebnisse und Zwischenergebnisse
        - dgm_pfad (str): Pfad zum aktuellen digitalen Geländemodell
        - mehrere_operate (bool): bei "True" werden mehrere Operate anhand von "mehrere_operate_input" hinzugefügt
        - mehrere_operate_input (list): Liste von Operaten, die auf einmal hinzugefügt werden sollen
        - stereo_modell_erstellen (bool): bei "True" wird das Stereo Modell zum Schluss erstellt
        - meridianstreifen_pfad (str): Pfad zur Meridianstreifen-Featureclass
        - externe_prj_sammlung (str): Pfad zu Verzeichnis mit zusätzlichen .prj-Dateien
        - datenquelle (str): Pfad des Verzeichnisses, in dem sich die Basisdaten, prj-Dateien und Luftbilder, befinden.
    """

    # Falls mehrere Operate auf einmal eingefügt werden sollen
    if mehrere_operate:
        # Füge alle Bilder zu den Mosaic Datasets hinzu
        for meridian_operat in mehrere_operate_input:
            main(
                speicherort,
                mehrere_operate,
                meridian_operat,
                meridianstreifen_pfad,
                dgm_pfad,
                externe_prj_sammlung,
                datenquelle
            )

        # Berechne die Stereo-Modelle der Meridiane, deren Operate eingefügt wurden
        if stereo_modell_erstellen:
            bearbeitete_meridiane = set(item[0] for item in mehrere_operate_input)
            for meridian in bearbeitete_meridiane:
                mosaic = rf"{speicherort}\{meridian}_mosaic.gdb\mosaic"
                create_stereo_model(mosaic)

    # Falls nur ein Operat eingefügt wird
    elif not mehrere_operate:
        workspace_info = main(
            speicherort,
            mehrere_operate,
            " ",
            meridianstreifen_pfad,
            dgm_pfad,
            externe_prj_sammlung,
            datenquelle
        )

        # Berechne das Stereo-Modell
        if stereo_modell_erstellen:
            meridian, epsg, operat, speicherort, meridianordner, operatordner, gdb, fds_final, fds_temp = workspace_info
            mosaic = rf"{speicherort}\{meridian}_mosaic.gdb\mosaic"
            create_stereo_model(mosaic)


@func_info
def main(speicherort, mehrere_operate, mehrere_operate_input, meridianstreifen_pfad, dgm_pfad, externe_prj_sammlung, datenquelle):
    """
    Diese Funktion steuert alle Skripts und darin enthaltene Funktionen an.
    Parameter:
        - speicherort (str): Pfad des Speicherorts sämtlicher Ergebnisse und Zwischenergebnisse
        - mehrere_operate (bool): bei "True" werden mehrere Operate anhand von "mehrere_operate_input" hinzugefügt
        - mehrere_operate_input (list): Liste von Operaten, die auf einmal hinzugefügt werden sollen
        - meridianstreifen_pfad (str): Pfad zur Meridianstreifen-Featureclass
        - dgm_pfad (str): Pfad zum aktuellen digitalen Geländemodell
        - externe_prj_sammlung (str): Pfad zu Verzeichnis mit zusätzlichen .prj-Dateien
        - datenquelle (str): Pfad des Verzeichnisses, in dem sich die Basisdaten, prj-Dateien und Luftbilder, befinden.
    Rückgabewert:
        - workspace_info (list): Liste aus Informationen zum Workspace
                                (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    """
    arcpy.env.overwriteOutput = True

    # User-Abfragen zu Meridian und Operat.
    if not mehrere_operate:
        meridian = workspace_funktionen.meridian_abfragen()
        operat = workspace_funktionen.operat_abfragen()
    else:
        meridian, operat = mehrere_operate_input

    # Informationen zum Workspace in "workspace_info".
    workspace_info = workspace_funktionen.workspace_info_konfigurieren(
        meridian,
        operat,
        speicherort
    )

    # Featureclasses werden erstellt und Pfade in "main_featureclasses_info" gespeichert.
    main_featureclasses_info = workspace_funktionen.featureclasses_erstellen(
        workspace_info
    )

    # Meridianstreifen Geodatabase wird erstellt.
    meridianstreifen, oesterreich_buffer = workspace_funktionen.meridianstreifen_gdb_erstellen(
        workspace_info,
        meridianstreifen_pfad
    )

    # Die passende(n) .prj-Datei(en) wird/werden gesucht und als Liste zurückgegeben.
    datenquelle_prj = prj_funktionen.prj_datei_suchen(
        datenquelle,
        workspace_info
    )

    if not datenquelle_prj:
        # keine .prj-Datei gefunden, externe prj-Sammlung wird durchsucht.
        datenquelle_prj = [prj_funktionen.externe_prj_sammlung_durchsuchen(externe_prj_sammlung, workspace_info)]

    # 2 Kopie pro prj.-Datei werden erstellt (1x original, 1x zur Weiterverarbeitung).
    prj_kopie_pfade = prj_funktionen.prj_kopieren(
        datenquelle_prj,
        workspace_info
    )

    # Zusammenfügen der prj.-Dateien, falls mehrere für ein Operat vorhanden sind.
    prj_kopie = prj_funktionen.mehrere_suboperate_check(
        prj_kopie_pfade,
        workspace_info
    )

    # relevante Zeilen aus "prj_kopie" extrahieren.
    bild_info_unbearbeitet = prj_funktionen.bild_info_extrahieren(
        prj_kopie
    )

    # Bereinigung der Bildinformation
    bild_info = prj_funktionen.bild_info_editieren(
        bild_info_unbearbeitet
    )

    # Bildpunkte werden in "bildpunkte_unbearbeitet" eingefügt
    vektor_lokal.bildpunkte_einfuegen(
        bild_info,
        main_featureclasses_info,
        workspace_info
    )

    # Check, ob die Flugstreifen und deren Benennung bereits ermittelt wurden
    json_benennung_datei = rf"{speicherort}\name_flugstreifen.json"
    flugstreifen_info = flugstreifen_benennung.benennung_info_check(
        json_benennung_datei,
        workspace_info
    )

    # "flugstreifen_info" wurde noch nicht ermittelt
    if not flugstreifen_info:
        # Struktur der Benennung (Trennzeichen, Subparts) wird ermittelt
        trennzeichen, split_liste, bildpunkt_liste = flugstreifen_benennung.benennung_struktur_erfassen(
            main_featureclasses_info
        )

        # Überprüfung, ob Code mit der aktuellen Flugstreifen-Benennung kompatibel ist
        flugstreifen_benennung.test_code_kompatibilitaet(
            split_liste
        )

        # Erfassung, wie oft sich Subparts innerhalb eines Samples wiederholen (niedrigster Wert entspricht Bildname)
        match_count_liste, sample = flugstreifen_benennung.match_subparts(
            split_liste,
            workspace_info
        )

        # Subpart mit den wenigsten Wiederholungen innerhalb des Samples wird eliminiert, falls Punkte auf Linie liegen
        # ist "flugstreifen_ermitteln" abgeschlossen, sonst nächsten Subpart eliminieren.
        flugstreifen_info = flugstreifen_benennung.flugstreifen_ermitteln(
            match_count_liste,
            sample,
            trennzeichen,
            bildpunkt_liste,
            workspace_info
        )

        # Flugstreifen-Benennung wird in json-Datei geschrieben
        flugstreifen_benennung.benennung_info_schreiben(
            json_benennung_datei,
            flugstreifen_info,
            workspace_info
        )

    # Update Featureclasses "bildpunkte_unbearbeitet" und "bildpunkte_extrahiert" mit Flugstreifen-Benennung
    vektor_lokal.bildpunkte_inkl_flugstreifen_info(
        bild_info,
        flugstreifen_info,
        main_featureclasses_info,
        workspace_info
    )

    # Flugstreifen wird auf Basis des Feldes "flugstreifen" in "bildpunkte_extrahiert" erstellt
    flugstreifen_unbearbeitet = vektor_lokal.flugstreifen_erstellen(
        main_featureclasses_info,
        workspace_info
    )

    # Flugstreifen außerhalb von Ö werden ermittelt und entsprechende Bildpunkte gelöscht
    flugstreifen_ausserhalb = vektor_lokal.flugstreifen_ganz_ausserhalb(
        flugstreifen_unbearbeitet,
        oesterreich_buffer,
        main_featureclasses_info,
        workspace_info
    )

    # Flugstreifen Richtung wird ermittelt und in Featureclasses kopiert
    flugstreifen_schraeg, flugstreifen_vertikal, flugstreifen_horizontal = vektor_lokal.flugstreifen_richtung_berechnen(
        flugstreifen_unbearbeitet,
        workspace_info
    )

    # Nur schräge Flugstreifen werden beibehalten, und je nach Relevanz entsprechender Liste hinzugefügt
    schraege_flugstreifen_liste, ungunst_schraeg = vektor_lokal.schraege_flugstreifen(
        flugstreifen_schraeg
    )

    # Nur vertikale Flugstreifen werden beibehalten
    vektor_lokal.vertikale_flugstreifen(
        flugstreifen_vertikal
    )
    # Nur horizontale Flugstreifen werden beibehalten
    vektor_lokal.horizontale_flugstreifen(
        flugstreifen_horizontal
    )

    # Namen der schrägen Flugstreifen, die gelöscht wurden, in "flugstreifen_ungunst" gespeichert
    flugstreifen_ungunst = vektor_lokal.schraege_randstreifen_extrahieren(
        flugstreifen_schraeg,
        flugstreifen_ausserhalb,
        meridianstreifen,
        ungunst_schraeg,
        workspace_info
    )

    # Bildpunkte in "bildpunkte_extrahiert" entsprechend flugstreifen_ungunst löschen
    vektor_lokal.schraege_randstreifen_bildpunkte_loeschen(
        main_featureclasses_info,
        flugstreifen_ungunst
    )

    # Bildpunkte horizontaler Flugstreifen werden vorgezogen, vertikale Flugstreifen Bildpunkte werden vorerst gelöscht
    vektor_lokal.vertikale_streifen_bildpunkte_loeschen(
        main_featureclasses_info,
        flugstreifen_vertikal
    )

    # benötigte vertikale Flugstreifen werden ermittelt
    vertikale_punkte_notwendig, vertikal_streifen_bereich_inland = vektor_lokal.vertikale_flugstreifen_benoetigt(
        flugstreifen_horizontal,
        flugstreifen_vertikal,
        workspace_info
    )

    if vertikale_punkte_notwendig:
        # Einfügen vertikaler Punkte ist notwendig
        # Bildpunkte werden entsprechend der benötigten vertikalen Flugstreifen eingefügt
        vektor_lokal.vertikale_flugstreifen_punkte_einfuegen(
            schraege_flugstreifen_liste,
            vertikal_streifen_bereich_inland,
            main_featureclasses_info,
            workspace_info
        )

    # Talstreifen-Bildpunkte werden freigeschnitten
    vektor_lokal.punkte_talstreifen_ausschneiden(
        main_featureclasses_info,
        schraege_flugstreifen_liste,
        workspace_info
    )

    # Erstellung aller nötigen gdb, fds und fc für die Zusammenführung
    global_info = workspace_funktionen.global_gdb_erstellen(
        workspace_info
    )

    # Erstellung der Operatsfläche des aktuellen Operates
    operatsflaeche = vektor_global.operat_flaeche_erstellen(
        main_featureclasses_info,
        workspace_info
    )

    # Hinzufügen der aktuellen Operatsfläche zu "flaechen_sammlung"
    vektor_global.flaechen_sammlung_befuellen(
        operatsflaeche,
        global_info,
        workspace_info
    )

    # Erstellung einer Featureclass mit Geometrie der Überschneidung und Informationen zu den schneidenden Operaten
    kombininierte_operat_ueberschneidungen = vektor_global.operat_ueberschneidungen(
        global_info
    )

    # Erstellung einer fc mit korrekt zugeordneten Überschneidungen, 2 Listen mit Bezug der Überschneidungen auf Input
    zu_input_anfuegen, nicht_zu_input_anfuegen, extrahierte_operat_ueberschneidungen = \
        vektor_global.aktuelle_operate_extrahieren(
            kombininierte_operat_ueberschneidungen,
            global_info,
            workspace_info
        )

    # Featureclass mit den korrekt zugeordneten Überschneidungsflächen wird erstellt
    flaechen_sammlung_final, input_operat_ohne_ueberschneidungen = vektor_global.flaechen_sammlung_zusammenfuegen(
        extrahierte_operat_ueberschneidungen,
        global_info,
        workspace_info
    )

    # Featureclasses mit Information zu Flächen des Input-Operates werden erstellt
    fc_zu_input_anfuegen, fc_input_operat_ohne_ueberschneidungen = vektor_global.input_operat_aufteilen(
        zu_input_anfuegen,
        input_operat_ohne_ueberschneidungen,
        global_info
    )

    # Alle Punkte, die gelöscht werden müssen, oder neu hinzugefügt werden, werden in Listen gespeichert
    loesch_punkte_liste, hinzugefuegt_punkte_liste = vektor_global.punkte_ausschneiden_hinzufuegen(
        fc_zu_input_anfuegen,
        fc_input_operat_ohne_ueberschneidungen,
        global_info,
        main_featureclasses_info
    )

    # Alle Namen der Operate, die zur Gänze ausserhalb von Ö liegen, werden in "operate_ausserhalb" gespeichert
    operate_ausserhalb = vektor_global.ausland_operate_bestimmen(
        flaechen_sammlung_final,
        global_info,
        workspace_info
    )

    # Die Pfade in der .prj-Datei werden angepasst anhand von "hinzugefuegt_punkte_liste"
    prj_dateien = prj_funktionen.prj_umschreiben(
        hinzugefuegt_punkte_liste,
        workspace_info
    )

    # Erstelle Geodatabase und Mosaic Dataset
    mosaic_dataset = raster_global.raster_workspace_erstellen(
        workspace_info
    )

    """    
    # Lösche veraltete Bilder aus Mosaic Dataset
    raster_global.bilder_aus_mosaic_entfernen(
        mosaic_dataset,
        loesch_punkte_liste
    )

    # Alle benötigten Raster werden zum Mosaic Dataset hinzugefügt
    raster_global.raster_zu_mosaic_hinzufuegen(
        mosaic_dataset,
        prj_dateien,
        dgm_pfad,
        workspace_info
    )

    # Lösche alle Raster der Operate, die zur Gänze außerhalb von Ö liegen
    raster_global.operate_ausserhalb_loeschen(
        mosaic_dataset,
        operate_ausserhalb
    )"""

    return workspace_info


@func_info
def create_stereo_model(mosaic: str):
    """
    Wurde im input.py file 'stereo_modell_erstellen = True' gewählt, wird als letzter Schritt das Stereo Modell
    erstellt.
    Parameter:
        - mosaic (str): Pfad zum Mosaic Dataset, für das ein Stereo Modell erstellt werden soll
    """

    print("\nDas Stereo Model wird erstellt...")
    print(mosaic)
    arcpy.BuildStereoModel_management(mosaic, same_flight="SAMEFLIGHT")
    print("Das Stereo Model wurde erfolgreich erstellt")


