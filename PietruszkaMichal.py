import arcpy, csv, os
from arcpy import env
import pythonaddins

#wczytanie danych
layer_b=arcpy.mapping.Layer(arcpy.GetParameterAsText(0))
layer_h=arcpy.mapping.Layer(arcpy.GetParameterAsText(1))
layer_nmt=arcpy.mapping.Layer(arcpy.GetParameterAsText(2))

#dodanie warstwy z budynkami do widoku
mxd = arcpy.mapping.MapDocument("CURRENT")
df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
arcpy.mapping.AddLayer(df, layer_b,"BOTTOM")

#ustawienie obszaru roboczego
folder = "C:/Users/Pietruszka/Desktop/PAg/dane/tera"
arcpy.env.workspace = folder

#konwersja NMT do TIN potrzebne dalej
arcpy.RasterTin_3d(layer_nmt, "tin_nmt")

#kod wykonywany w przypadku gdy 2. wczytana warstwa to punkty reprezentacyjne wysokościowe
if layer_h.isFeatureLayer:
  arcpy.SpatialJoin_analysis(layer_b, layer_h, "sjpoints.shp")
  arcpy.AddField_management(layer_b, "hNMPT1", "LONG")   #przechowuje absolutna wysokosc budynku z NMPT
  arcpy.AddField_management(layer_b, "heightZ", "LONG")  #przechowuje tylko rzeczywista wysokosc budynku

  arcpy.sa.ZonalStatisticsAsTable(layer_b,"FID",layer_nmt,"table_nmt.dbf","NODATA","MAXIMUM")

  liczba_bud=int(arcpy.GetCount_management(layer_b).getOutput(0))
  arcpy.AddMessage("Has {0} features.".format(liczba_bud))

  #przepisywanie danych z warstwy spatial join do warstwy budynków
  licznik=0
  while licznik < liczba_bud:
    value_nmt = 0
    expression6 = arcpy.AddFieldDelimiters("table_nmt.dbf", "FID_") + ' = ' + str(licznik)
    with arcpy.da.SearchCursor("table_nmt.dbf","MAX",expression6) as cursor6:
      for row in cursor6:
        if row is not None:
          value_nmt=row[0]
    expression5 = arcpy.AddFieldDelimiters("sjpoints.shp", "FID") + ' = ' + str(licznik)
    with arcpy.da.SearchCursor("sjpoints.shp","height",expression5) as cursor5:
      for row in cursor5:
        if row is not None:
          valueZ=row[0]
    expression4 = arcpy.AddFieldDelimiters(layer_b, "FID") + ' = ' + str(licznik)
    with arcpy.da.UpdateCursor(layer_b,"hNMPT1",expression4) as cursor7:
      for row in cursor7:
        if row is not None:
          row[0]=valueZ+value_nmt
          cursor7.updateRow(row)
    with arcpy.da.UpdateCursor(layer_b,"heightZ",expression4) as cursor4:
      for row in cursor4:
        if row is not None:
          row[0]=valueZ
          cursor4.updateRow(row)
    licznik+=1

  #stworzenie sztucznego TIN dla wysokości budynków+wysokości podstawy budynku z NMT
  arcpy.ddd.CreateTin("tin_h","",arcpy.GetParameterAsText(0) + " hNMPT1 masspoints","constrained_delaunay")
  #stworzenie właściwego modelu, Multipatch
  arcpy.ExtrudeBetween_3d ("tin_h", "tin_nmt", layer_b, "wynik2")

  #zapis id budynków gdzie nie znaleziono danych o wysokościach, pusty spatial join
  text_file = open(folder+"/log.txt", "w")
  fieldnames = [field.name for field in arcpy.ListFields(layer_b)]
  for row in arcpy.SearchCursor(layer_b):
   if row.getValue(fieldnames[-1])==0:
     text_file.write("Nie znaleziono wartosci dla FID = %s\n" % row.getValue(fieldnames[0]))
   del row
  text_file.close()

#kod wykonywany w przypadku gdy 2. wczytana warstwa to Numeryczny Model Pokrycia Terenu
if layer_h.isRasterLayer:
  arcpy.sa.ZonalStatisticsAsTable(layer_b,"FID",layer_h,"table_nmpt.dbf","NODATA","MAXIMUM")
  arcpy.sa.ZonalStatisticsAsTable(layer_b,"FID",layer_nmt,"table_nmt.dbf","NODATA","MAXIMUM")
  licznik = 0

  arcpy.AddField_management(layer_b, "hNMPT2", "DOUBLE")
  liczba_bud=int(arcpy.GetCount_management(layer_b).getOutput(0))+1

  #wyciągnięcie informacji o wysokości z NMT i NMPT, odjęcie ich i przepisanie do odpowiednich obiektów
  while licznik < liczba_bud:
   value_nmt=0
   value_nmpt=0
   expression = arcpy.AddFieldDelimiters("table_nmpt.dbf", "FID_") + ' = ' + str(licznik)
   with arcpy.da.SearchCursor("table_nmpt.dbf","MAX",expression) as cursor1:
      for row in cursor1:
        if row is not None:
          value_nmpt=row[0]
   expression2 = arcpy.AddFieldDelimiters("table_nmt.dbf", "FID_") + ' = ' + str(licznik)
   with arcpy.da.SearchCursor("table_nmt.dbf","MAX",expression2) as cursor2:
      for row in cursor2:
        if row is not None:
          value_nmt=row[0]
   expression3 = arcpy.AddFieldDelimiters(layer_b, "FID") + ' = ' + str(licznik)
   with arcpy.da.UpdateCursor(layer_b,"hNMPT2",expression3) as cursor3:
      for row in cursor3:
        if row is not None:
          row[0]=value_nmpt-value_nmt
          cursor3.updateRow(row)
   licznik+=1

  #konwersja NMPT do TIN
  arcpy.RasterTin_3d(layer_h, "tin_nmpt")
  #stworzenie właściwego modelu, Multipatch
  arcpy.ExtrudeBetween_3d ("tin_nmpt", "tin_nmt", layer_b, "wynik1")

  #zapis id budynków gdzie nie znaleziono danych lub są one nieakceptowalne
  text_file = open(folder+"/log.txt", "w")
  fieldnames = [field.name for field in arcpy.ListFields(layer_b)]
  for row in arcpy.SearchCursor(layer_b):
    if row.getValue(fieldnames[-1])<=0 or row.getValue(fieldnames[-2])<=0:
      text_file.write("Nie znaleziono wartosci dla FID = %s\n" % row.getValue(fieldnames[0]))
    del row
  text_file.close()
