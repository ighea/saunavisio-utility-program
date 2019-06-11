#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys,os,time,urllib2,cookielib
import threading
import pickle
import signal

try:
	import saunavisio
	from saunavisio import SaunaVisio
except Exception, value:
	print "!!! Virhe ladattaessa SaunaVisio-moduulia! Tarkista että käytössäsi on uusin saunavisio.py!"
	print "Poikkeus: ",value
	sys.exit()

try:
	import gobject
	import gtk
	# Windows-purkkaa, duh :<
	if (saunavisio.isWindowsOS()):
		gobject.threads_init()
	else:
		gtk.gdk.threads_init()
except Exception, value:
	print "!!! Virhe ladattaessa PyGTK:ta, tarkista että se on asennettuna! Lisätietoja LUEMINUT_GUI:ssa! !!!"
	print "Poikkeus: ", value
	sys.exit()


SEARCHRESULT_COLUMN_ID=0
SEARCHRESULT_COLUMN_CHANNEL=1
SEARCHRESULT_COLUMN_DATE=2
SEARCHRESULT_COLUMN_RUNTIME=3
SEARCHRESULT_COLUMN_NAME=4
SEARCHRESULT_COLUMN_DESCRIPTION=5
SEARCHRESULT_COLUMN_STATE=6
SEARCHRESULT_COLUMN_COLOR=7

class ExceptionHandler(threading.Thread):
	'''Esittää poikkeukset gtk-dialogina'''
	def __init__(self, exceptionvalue=""):
		threading.Thread.__init__(self)
		self.exceptionvalue = exceptionvalue
		return
	
	# Windows fixejä, duh
	if (saunavisio.isWindowsOS()):
		def start(self):
			gobject.idle_add(self.run)
			
	def run(self):
		try:	
			
			gtk.gdk.threads_enter()
			dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_CLOSE, message_format="Ohjelmaa suorittaessa tapahtui seuraava virhe:\n\n"+str(self.exceptionvalue))
			dialog.set_title("Virhe!")
			dialog.run()
			dialog.destroy()
			gtk.gdk.threads_leave()
		except Exception, value:
			gtk.gdk.threads_leave()
			print "No nyt meni hämäräksi!"
			print "Poikkeus", value
			gtk.gdk.threads_leave()
		return

class GUI:

	class SettingsDialog:
		def __init__(self, parent):
			self.parent = parent
			self.Window = gtk.Window()
			self.Window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
			self.Window.set_title("Asetukset")
			self.Window.set_resizable(False)
			self.Window.set_transient_for(self.parent.MainWindow)
			#self.Window.set_size_request(500,400)
			self.Window.connect("delete_event", self.Window_deleteevent_callback)
			
			self.LabelUsername = gtk.Label("Tunnus:")
			self.EntryUsername = gtk.Entry()
			self.EntryUsername.set_text(self.parent.saunavisio.Config.get("username") )

			self.LabelPassword = gtk.Label("Salasana:")
			self.EntryPassword = gtk.Entry()
			self.EntryPassword.set_tooltip_text("Salasanaa EI ole kryptattu/salattu, vaan se löytyy selväkielisenä asetustiedostosta.")
			self.EntryPassword.set_visibility(False)
			self.EntryPassword.set_text(self.parent.saunavisio.Config.get("password"))

			self.LabelVideoPlayer = gtk.Label("Videosoitin:")
			self.EntryVideoPlayer = gtk.Entry()
			self.EntryVideoPlayer.set_tooltip_text("Aseta tähän videosoitin koko polkuineen, jolla haluat toistaa tallenteet ja katsella NettiVisiota. Suositellaan VLC:tä.")
			self.EntryVideoPlayer.set_text(self.parent.saunavisio.Config.get("videoplayer"))

			self.EntryDownloadDirectory = gtk.Label("Hakemisto latauksille:")
			self.FileChooserButtonDownloadDirectory = gtk.FileChooserButton('Valitse hakemisto')
			self.FileChooserButtonDownloadDirectory.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
			self.FileChooserButtonDownloadDirectory.set_current_folder(self.parent.saunavisio.Config.get("downloaddirectory"))

			self.CheckButtonDownloadUseSubDirs = gtk.CheckButton()
			self.CheckButtonDownloadUseSubDirs.set_label("Käytä latauksille alihakemistoja")
			self.CheckButtonDownloadUseSubDirs.set_tooltip_text("Tallentaa lataukset yllä valitsemaasi hakemistoon käyttäen alihakemiston nimenä ohjelman nimeä: 'Lataukset\\Ohjelma\\Ohjelma.ts'")
			self.CheckButtonDownloadUseSubDirs.set_active(self.parent.saunavisio.Config.get("downloadUseSubDirs"))

			self.CheckButtonDoUpdateCheck = gtk.CheckButton("Tarkista päivitykset")
			self.CheckButtonDoUpdateCheck.set_active(self.parent.saunavisio.doUpdateCheck)
			
			#ShowThumbnails
			self.CheckButtonShowThumbnails = gtk.CheckButton("Näytä esikatselukuvat")
			self.CheckButtonShowThumbnails.set_tooltip_text("Lataa ja näyttää tallennetuille ohjelmille esikatselukuvat. Poistamalla valinnan säästät mobiili-laajakaistoilla aikaa ja mahdollisesti rahaa.")
			self.parent.ShowThumbnails = self.parent.saunavisio.Config.get("showthumbnails")
			self.CheckButtonShowThumbnails.set_active(self.parent.ShowThumbnails)
			
			#StoreVisibilitySettings
			self.CheckButtonStoreVisibilitySettings = gtk.CheckButton("Muista hakujen näkyvyysasetukset")
			self.CheckButtonStoreVisibilitySettings.set_tooltip_text("Muistaa viimeksi käytetyt näkyvyysasetukset hauilla pääikkunassa")
			StoreVisibilitySettings = self.parent.saunavisio.Config.get("StoreVisibilitySettings")
			if (type(StoreVisibilitySettings) == str):
				self.parent.StoreVisibilitySettings = False
			else:
				self.parent.StoreVisibilitySettings = StoreVisibilitySettings
			self.CheckButtonStoreVisibilitySettings.set_active(self.parent.StoreVisibilitySettings)

			#CheckStoredPrograms
			self.CheckButtonCheckStoredPrograms = gtk.CheckButton("Näytä tallenteet levyllä")
			self.CheckButtonCheckStoredPrograms.set_tooltip_text("Esittää koneelle ladatatut tallenteet eri sävyllä ohjelmalistauksissa, kuin ohjelmat, joiden tallentaminen on valmistunut. Tämän asetuksen ollessa päällä, sävytetyn ohjelma-tallenteen toiston aloittaminen toistaa videon suoraan paikallisesti.")
			self.parent.CheckStoredPrograms = self.parent.saunavisio.Config.get("CheckStoredPrograms", bool)
			self.CheckButtonCheckStoredPrograms.set_active(self.parent.CheckStoredPrograms)

			# AutoFetchProgramInfo
			self.CheckButtonAutoFetchProgramInfo = gtk.CheckButton("Nouda ohjelmatiedot automaattisesti")
			self.CheckButtonAutoFetchProgramInfo.set_tooltip_text("Noutaa automaattisesti taustalla ohjelmien ohjelmatietoja.")
			self.parent.AutoFetchProgramInfo = self.parent.saunavisio.Config.get("AutoFetchProgramInfo", bool)
			self.CheckButtonAutoFetchProgramInfo.set_active(self.parent.AutoFetchProgramInfo)
					 

			self.ButtonClose = gtk.Button("Sulje",gtk.STOCK_CLOSE)
			self.ButtonClose.set_tooltip_text("Sulje tämä ikkuna ja tallenna muutokset.")
			self.ButtonClose.connect("clicked", self.ButtonClose_clicked_callback)

			VBoxFrameWindowBase = gtk.VBox()
			FrameWindowBase = gtk.Frame()
			VBoxWindowBase = gtk.VBox()
			VBoxWindowBase.set_spacing(5)
			FrameUserSettings = gtk.Frame("SaunaVisio-tunnukset")
			HBoxFrameUserSettings = gtk.HBox()
			HBoxFrameUserSettings.set_spacing(5)
			HBoxDownloadDirectory = gtk.HBox()
			HBoxDownloadDirectory.set_spacing(5)
			HBoxVideoPlayer = gtk.HBox()
			HBoxVideoPlayer.set_spacing(5)
			HBoxButtons = gtk.HBox()
			
			self.Window.add(VBoxFrameWindowBase)
			VBoxFrameWindowBase.pack_start(FrameWindowBase)
			FrameWindowBase.add(VBoxWindowBase)
			VBoxWindowBase.pack_start(FrameUserSettings)
			FrameUserSettings.add(HBoxFrameUserSettings)
			HBoxFrameUserSettings.pack_start(self.LabelUsername)
			HBoxFrameUserSettings.pack_start(self.EntryUsername)
			HBoxFrameUserSettings.pack_start(self.LabelPassword)
			HBoxFrameUserSettings.pack_start(self.EntryPassword)
			VBoxWindowBase.pack_start(HBoxVideoPlayer)
			HBoxVideoPlayer.pack_start(self.LabelVideoPlayer, False,False)
			HBoxVideoPlayer.pack_start(self.EntryVideoPlayer)
			VBoxWindowBase.pack_start(HBoxDownloadDirectory)
			HBoxDownloadDirectory.pack_start(self.EntryDownloadDirectory, False, False)
			HBoxDownloadDirectory.pack_start(self.FileChooserButtonDownloadDirectory)
			VBoxWindowBase.pack_start(self.CheckButtonDownloadUseSubDirs)
			VBoxWindowBase.pack_start(self.CheckButtonDoUpdateCheck)
			VBoxWindowBase.pack_start(self.CheckButtonShowThumbnails)
			VBoxWindowBase.pack_start(self.CheckButtonStoreVisibilitySettings)
			VBoxWindowBase.pack_start(self.CheckButtonCheckStoredPrograms)
			VBoxWindowBase.pack_start(self.CheckButtonAutoFetchProgramInfo)
			VBoxFrameWindowBase.pack_start(HBoxButtons)
			HBoxButtons.pack_start(self.ButtonClose, True, False)
		
			return
		
		
		def SetAndSaveSettings(self):
			# showthumbnails ei ole osa SaunaVisio-luokkaa, joten asetetaan se täällä erikseen asetuksiin

			# StoreVisibilitySettings, tallennetaan uudet muutokset vain jos niin on tahdottu
			self.parent.saunavisio.Config.set("StoreVisibilitySettings", self.CheckButtonStoreVisibilitySettings.get_active())
			self.parent.StoreVisibilitySettings = self.CheckButtonStoreVisibilitySettings.get_active()

#		self.CheckStoredPrograms = True
#		self.AutoFetchProgramInfo = True

			# CheckStoredPrograms
			self.parent.CheckStoredPrograms = self.CheckButtonCheckStoredPrograms.get_active()
			self.parent.saunavisio.Config.set("CheckStoredPrograms", self.CheckButtonCheckStoredPrograms.get_active())

			# AutoFetchProgramInfo
			self.parent.AutoFetchProgramInfo = self.CheckButtonAutoFetchProgramInfo.get_active()
			self.parent.saunavisio.Config.set("AutoFetchProgramInfo", self.CheckButtonAutoFetchProgramInfo.get_active())
	

			self.parent.ShowThumbnails = self.CheckButtonShowThumbnails.get_active()
			self.parent.saunavisio.Config.set("showthumbnails", self.CheckButtonShowThumbnails.get_active())

			self.parent.saunavisio.downloadUseSubDirs = self.CheckButtonDownloadUseSubDirs.get_active()
			self.parent.saunavisio.doUpdateCheck = self.CheckButtonDoUpdateCheck.get_active()
						
			self.parent.saunavisio.downloaddirectory = self.FileChooserButtonDownloadDirectory.get_filename()
			
			self.parent.saunavisio.username = self.EntryUsername.get_text()
			self.parent.saunavisio.password = self.EntryPassword.get_text()
			self.parent.saunavisio.videoplayer = self.EntryVideoPlayer.get_text()
			
			self.parent.saunavisio.saveSettings()		
			return
			
		def ButtonClose_clicked_callback(self, widget):
			self.SetAndSaveSettings()
			self.hide()
			return
		
		def Window_deleteevent_callback(self, widget, event):
			self.hide()
			# Ei tuhota ikkunaan vaan pistetään vain piiloon
			return True
			
		def show(self):
			self.Window.show_all()
			return
		
		
		def hide(self):
			self.Window.hide_all()
			return


	class DownloaderDialog:
			
		def __init__(self, parent):
		
			self.parent = parent
			
			self.TREEVIEW_COLUMN_ID = 0
			self.TREEVIEW_COLUMN_PERCENT = 1
			self.TREEVIEW_COLUMN_TRANSFER = 2
			self.TREEVIEW_COLUMN_NAME = 3
			self.TREEVIEW_COLUMN_TOOLTIP = 4
			self.TREEVIEW_COLUMN_COLOR = 5
			
			
			self.Window = gtk.Window()
			self.Window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
			self.Window.set_size_request(320,220)
			self.Window.set_title("Tallenteiden lataaminen")
			self.Window.connect("delete_event", self.Window_close_callback)
			
			
			self.ListStore = gtk.ListStore(str,str,str, str, str, str)
			self.TreeView = gtk.TreeView(self.ListStore)
			self.TreeView.set_reorderable(True)
			
			self.TreeView.append_column(gtk.TreeViewColumn('ID', gtk.CellRendererText(), text=self.TREEVIEW_COLUMN_ID, foreground=5))
			self.TreeView.append_column(gtk.TreeViewColumn('Valmis', gtk.CellRendererText(), text=self.TREEVIEW_COLUMN_PERCENT, foreground=5))
			self.TreeView.append_column(gtk.TreeViewColumn('Siirtonopeus', gtk.CellRendererText(), text=self.TREEVIEW_COLUMN_TRANSFER, foreground=5))
			self.TreeView.append_column(gtk.TreeViewColumn('Nimi', gtk.CellRendererText(), text=self.TREEVIEW_COLUMN_NAME, foreground=5))
			column = gtk.TreeViewColumn('Tooltip', gtk.CellRendererText(), text=self.TREEVIEW_COLUMN_TOOLTIP, foreground=5)
			self.TreeView.append_column(column)
			column.set_visible(False)

			column = gtk.TreeViewColumn('Color', gtk.CellRendererText(), text=self.TREEVIEW_COLUMN_COLOR)
			self.TreeView.append_column(column)
			column.set_visible(False)
			
			# Asetetaan yksi kolumni tooltippejä varten
			self.TreeView.set_tooltip_column(self.TREEVIEW_COLUMN_TOOLTIP)

			self.ScrolledWindowForTreeView = gtk.ScrolledWindow()
			self.ScrolledWindowForTreeView.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
			self.ScrolledWindowForTreeView.add(self.TreeView)


			self.ButtonDownloadStart = gtk.Button("Aloita")
			self.ButtonDownloadStart.connect("clicked", self.ButtonDownloadStart_clicked_callback)	
			self.ButtonDownloadCancel = gtk.Button("Peruuta")	
			self.ButtonDownloadCancel.connect("clicked", self.ButtonDownloadCancel_clicked_callback)

			#self.ButtonsHBox = gtk.HBox()
			#self.ButtonsHBox.set_spacing(10)
			#self.ButtonsHBox.pack_start(self.ButtonDownloadStart, True, True, 10)
			#self.ButtonsHBox.pack_start(self.ButtonDownloadCancel, True, True, 10)

			self.BaseVBox = gtk.VBox()
			self.BaseVBox.set_spacing(5)
			
			self.BaseVBox.pack_start(self.ScrolledWindowForTreeView)
			#self.BaseVBox.pack_start(self.ButtonsHBox, False)
			self.BaseVBox.pack_start(self.ButtonDownloadStart, False,False)
			self.BaseVBox.pack_start(self.ButtonDownloadCancel, False,False)
			self.Window.add(self.BaseVBox)
		
			self.programs = []
			self.dlLockSet = False
			self.downloading = False
			
			self.downloadThread = self.DownloadThread(self, [])

			return
		
				
		class DownloadThread(threading.Thread):
			#def __init__(self, parent, durl, destFilePath, destFileName, id ): 
			def __init__(self, parent, downloadIDList ): 
				threading.Thread.__init__ (self)
				self.parent = parent
				# Lista ladattavien ohjelmien ID:stä
				self.downloadIDList = downloadIDList

				self.running = True
				#self.process = None
				self.stopthread = threading.Event()
	
				print "created"
				return
				
			def run(self):
				print "Download thread: run"
				
				self.parent.downloading = True
				
				downloadNumber = 0
				for downloadID in self.downloadIDList:
					resuming = False
					
					if (not self.running):
						# Hoidetaan homma asteen nätimmin, poistutaan silmukasta
						print "Keskeytetään..."
						break
				
					print "Haetaan lataus URL tallenteelle"
					try:
						durl, id, programn, programdate, programtime, wgetcmd, pinfo, destFilePath, destFileName = self.parent.parent.saunavisio.fetchDownloadUrl(downloadID)
						self.setName(str(id)+":"+programn)
					except Exception, value:
						print "Ohjelmatietojen haussa tapahtui virhe!"
						print "Poikkeus: ", value
						try:
							gtk.gdk.threads_enter()
							dialog =  gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_CLOSE, message_format="Ohjelmatietoja ladattaessa tapahtui seuraava virhe:\n\n"+str(value))
							dialog.set_title("Virhe ladattaessa ohjelmatietoja")
							dialog.run()
							dialog.destroy()
							gtk.gdk.threads_leave()
						finally:
							gtk.gdk.threads_leave()
						break
						
						
					try:
						#print "Päivitetään ToolTip-kolumni"
						self.parent.ListStore[downloadNumber][self.parent.TREEVIEW_COLUMN_TOOLTIP] = programn + " ("+programdate+") "+programtime+"\n\n"+pinfo+"\n\nTiedosto: "+ destFilePath + destFileName
					
						# Luodaan lataushakemisto
						if (not os.path.exists(destFilePath)):
							print "Luodaan hakemisto '"+destFilePath+"'"
							os.mkdir(destFilePath)		
						
						# Ladattavan tiedoston koko sijainti
						dlFile = destFilePath+destFileName


						# Avataan kohde tiedosto kirjoitusta varten
						localFileSize = 0
						if (os.path.exists(dlFile)):
							print "Kohde tiedosto on jo olemassa, yritetään jatkaa siirtoa."
							resuming = True
							localFileSize = os.path.getsize(dlFile)
							outfile = open(dlFile, "ab")
						else:
							outfile = open(dlFile, "wb")
							
						# Luodaan pyyntö tiedostoa varten
						print dlFile, durl
						request = urllib2.Request(durl)
						request.add_header('User-Agent', "Mozilla/5.0 (X11; U; Linux i686; fi-FI; rv:1.9) Gecko/2008052912 Firefox/3.0")
						if (localFileSize > 0):
							request.add_header('Range', 'bytes=%d-' % (localFileSize, ))
					
						opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.parent.parent.saunavisio.cookieJar))
						# Suoritetaan pyyntö
						instream = opener.open(request)
						# Kaivetaan tiedoston koko palvelimella:
						filesize = float(instream.info().getheader("Content-Length"))
					
						print str(instream.info())
					
						# Asetetaan ladattavan ID:n rivi oranssiksi ilmoittamaan menossa olevasta latauksesta
						gtk.gdk.threads_enter()
						self.parent.ListStore[downloadNumber][self.parent.TREEVIEW_COLUMN_COLOR] = "orange"
						gtk.gdk.threads_leave()
										
					
						# Latausnopeuden härdellöinti
						lastTime = time.time()
						percent_last=percent=0
						bytesReadDuringOneSec = 0.0
					
						bytesRead=0.0
						# Jos tiedostoa on jo ladattuna levylle, korjaillaan ladatun datan määrä ja kokonais koko
						if (localFileSize > 0):
							if (resuming and filesize == 0):
								# Lataus on jo valmis
								print "Tiedosto on jo kokonaan ladattuna levylle."
								percent = 100
							bytesRead = localFileSize
							filesize = filesize + localFileSize
					
						# Varsinainen lataus-silmukka alkaa
						print "Aloitetaan tallenteen lataus."
						for line in instream:
							if (not self.running):
								# Keskeyttää lataamisen ja sulkee streamit, itse latausjonon juoksu lopetetaan
								# vasta "for programID"-silmukan alussa
								break
							bytesRead+=len(line)
							percent = 100*bytesRead/filesize
							if (int(percent) != int(percent_last)):
								percent_last = int(percent)
								# print str(percent_last)+"% done! ("+str(int(bytesRead/1024))+"kt)", id, dlFile
								gtk.gdk.threads_enter()
								# Asetetaan prosentit oikeaan lohkohon:
								self.parent.ListStore[downloadNumber][self.parent.TREEVIEW_COLUMN_PERCENT] = str(int(percent))+"%"
								gtk.gdk.threads_leave()
	
							outfile.write(line)
						
							bytesReadDuringOneSec+=len(line)
							timeShift = time.time() - lastTime
							if (timeShift > 1.0):
								lastTime = time.time()
								bytesPerSec = bytesReadDuringOneSec / timeShift
								try:
									gtk.gdk.threads_enter()
									if (bytesPerSec > 10485760): # Jos latausnopeus yli 10Mt/s näytetään megatavuina
										self.parent.ListStore[downloadNumber][self.parent.TREEVIEW_COLUMN_TRANSFER] = str(int(bytesPerSec/1048576))+" Mt/s"
									elif (bytesPerSec > 10240): # Jos latausnopeus yli 10 kilotavun, niin kilotavuina
										self.parent.ListStore[downloadNumber][self.parent.TREEVIEW_COLUMN_TRANSFER] = str(int(bytesPerSec/1024))+" kt/s"
									else:	# Muutoin tavua sekunnissa
										self.parent.ListStore[downloadNumber][self.parent.TREEVIEW_COLUMN_TRANSFER] = str(int(bytesPerSec))+" t/s"
								finally:
									gtk.gdk.threads_leave()
								bytesReadDuringOneSec=0.0
						
						instream.close()
						outfile.flush()
						outfile.close()
					
						# Valmistumisväri:
						if (int(percent) == 100):
							self.parent.ListStore[downloadNumber][self.parent.TREEVIEW_COLUMN_COLOR] = "darkgreen"
							self.parent.ListStore[downloadNumber][self.parent.TREEVIEW_COLUMN_TRANSFER] = "Valmis"
							self.parent.ListStore[downloadNumber][self.parent.TREEVIEW_COLUMN_PERCENT] = "100 %"
							print "Yksi lataus valmis:", programn
							
						# Seuraava ladattava latausjonossa, kasvatetaan latauksen numeroa yhdellä
						downloadNumber += 1

					except Exception, value:
						gtk.gdk.threads_leave()
						print "Poikkeus:",value
						gtk.gdk.threads_enter()
						dialog =  gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_CLOSE, message_format="Ohjelmatietoja ladattaessa tapahtui seuraava virhe:\n\n"+str(value))
						dialog.set_title("Virhe ladattaessa ohjelmatietoja")
						dialog.run()
						dialog.destroy()
						gtk.gdk.threads_leave()

				# Lataus forri päättyy
				
				print "All done."
				# Jos viimeisimmän latauksen latausprosentti on täysi, niin heitetään otsikko uuteen uskoon 
				gtk.gdk.threads_enter()
				try:
					if (int(percent) == 100):
						self.parent.Window.set_title("Valmis - "+self.parent.Window.get_title())
						self.parent.ButtonDownloadStart.set_sensitive(False)
						self.parent.ButtonDownloadCancel.set_label("Sulje")
					else:
						self.parent.ListStore[downloadNumber-1][self.parent.TREEVIEW_COLUMN_COLOR] = "red"
						self.parent.ListStore[downloadNumber-1][self.parent.TREEVIEW_COLUMN_TRANSFER] = "Keskeytetty"
				finally:
					gtk.gdk.threads_leave()
						
				self.parent.downloading = False
				return


			def die(self):
				print "Tapetaan Thread:"
				print self.getName()
				self.running=False
				self.stopthread.set()
				

		def ButtonDownloadStart_clicked_callback(self, widget):
			if (self.ButtonDownloadStart.get_label() == "Aloita"):
				#widget.set_sensitive(False)
				self.TreeView.set_reorderable(False)
			
				#self.ButtonDownloadCancel.set_label("Keskeytä")
				self.ButtonDownloadStart.set_label("Keskeytä")

				downloadIDList=[]
			
				# Kerätään TreeViewistä ID:t listaan, jotta saadaan latausjärjestys kuntoon
				iter = self.ListStore.get_iter_first()
				while (iter != None):
					downloadIDList.append(self.ListStore.get_value(iter, self.TREEVIEW_COLUMN_ID))
					iter = self.ListStore.iter_next(iter)
				
				# Luodaan lataus-threadi ja viskastaan sille constructorissa ID-lista
				self.downloadThread = self.DownloadThread(self, downloadIDList)
				self.downloadThread.start()
				
				self.TreeView.get_selection().unselect_all()
			else: #Keskeytä
				self.ButtonDownloadStart.set_label("Aloita")
				# Palautetaan mahdollisuus vaihtaa järjestystä:
				self.TreeView.set_reorderable(True)
				# Käsketään nykyisen lataus-threadin sulkea itsensä
				self.downloadThread.die()
				
			return
				
		
		def ButtonDownloadCancel_clicked_callback(self, widget):
			if (self.downloading):
				dialog = gtk.MessageDialog(parent=self.Window, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Latauksia on käynnissä, haluatko varmasti keskeyttää ne?")
				dialog.set_title("Varmistus")
				resp = dialog.run()
				dialog.destroy()
				print resp
				if resp==gtk.RESPONSE_YES:
					print "yes"
				else:
					print "Toiminto peruttu"
					return True

			self.TreeView.set_reorderable(True)
			self.ButtonDownloadStart.set_sensitive(True)
			self.hide()
			self.downloadThread.die()
			# Poistaa itsensä DownloaderDialogList:stä... ruma rumaa ;P
			self.parent.DownloaderDialogList.remove(self)
			
			self.Window.destroy()

		
		def show(self, programlist=[]):
			self.TreeView.set_reorderable(True)
			self.programs = programlist
			self.ListStore.clear()
			self.ButtonDownloadCancel.set_label("Peruuta")

			for program in self.programs:
				print len(self.programs)
				ID, kanava, aika, nimi, kuvaus = program
				# ID, %-done, DL-speed, nimi, kuvaus 
				self.ListStore.append([ID, "0 %", "0 t/s", nimi, nimi+" ("+aika+")\n"+kuvaus, "black"])
			self.Window.show_all()
			
		
		def hide(self):
			self.Window.hide_all()
			

		def Window_close_callback(self, widget, event):
			if (self.downloading):
				dialog = gtk.MessageDialog(parent=self.Window, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Latauksia on käynnissä, haluatko varmasti keskeyttää ne?")
				dialog.set_title("Varmistus")
				resp = dialog.run()
				dialog.destroy()
				print resp
				if resp==gtk.RESPONSE_YES:
					print "yes"
				else:
					print "Toiminto peruttu"
					return True
		
			self.hide()
			self.downloadThread.die()
			print "DownloadDialog closed"
			#Ja annetaan akkunan mennä menojaan
			return False
			
			

	class SearchRunner(threading.Thread):
		def __init__(self, widget, searchwords, num):
			threading.Thread.__init__ (self)
			self.widget = widget
			self.searchwords = searchwords
			self.num = num
			return
	
		def run(self):
			try:
				searchdata = self.widget.saunavisio.getSearchData(self.searchwords, False)
			
				#gtk.gdk.threads_enter()
				self.widget.showSearchResults(searchdata, self.widget.SearchNewCheckButton.get_active(),self.widget.SearchRequestedCheckButton.get_active(),self.widget.SearchRecordedCheckButton.get_active() )
			
				if (len(searchdata) == 0):
					self.widget.StatusLabel.set_text("Tiedot noudettu: Ei osumia!")
				else:
					self.widget.StatusLabel.set_text("Tiedot noudettu!")
				#print self.num, "Done."
			except Exception, value:
				eh = ExceptionHandler(value)
				eh.start()
			return

	class Dictionary:
		def __init__(self, parent_widget, datafile):
			self.widget = parent_widget
			self.data = {}
			self.file = datafile
			
		def load(self):
			if (os.path.exists(self.file)):
				f = open(self.file, 'r')
				self.data = pickle.load(f)
				f.close()
			else:
				print "Tiedostoa '"+self.file+"' ei ole olemassa, ei välitetä siitä!"
			
		def save(self):
			try:
				f = open(self.file, 'w')
				pickle.dump(self.data, f)
				f.close()
			except IOError, value:
				print "Virhe kirjoitettaessa tiedostoon '"+self.file+"'!", value
		
		def append(self, key, value):
			self.data[key] = value
		
		def find(self, key):
			return self.data[key]
			
		def clear(self):
			self.data.clear()


	# Alustellaan luokka/sovellus
	def __init__(self):
	
		self.version = 0.22
		self.searchResultColorNew=None
		self.searchResultColorRequested="red"
		self.searchResultColorRecorded="darkgreen"
		self.searchResultColorOndisk="blue"
		
		self.thread_count = 0
		self.ShowThumbnails = True
		self.StoreVisibilitySettings = False
		
		self.CheckStoredPrograms = True
		self.AutoFetchProgramInfo = True

		# SaunaVisio-stuffi	
		self.saunavisio = SaunaVisio()
		
		self.saunavisio_version = self.saunavisio.getVersion()

		if (self.saunavisio.loadSettings()):		
			print "*** SaunaVision asetukset ladattu onnistuneesti!"
		else:
			print "*** SaunaVision asetuksia ladatessa tapahtui virhe!"

		self.saunavisio.checkUsernameAndPassword(True)

		# Sanakirja sisältäen ID:tä ja kuvauksia
		self.idDictionary = self.Dictionary(self, self.saunavisio.configdirectory+"dict.txt")
		self.idDictionary.load()

		#self.programDownloader = self.DownloaderDialog(self)

		# GTK-kama
		self.MainWindow = gtk.Window()
		self.MainWindow.set_position(gtk.WIN_POS_CENTER_ALWAYS)
		try:
			self.MainWindow.set_icon_from_file("saunavisio.ico")
		except Exception, value:
			print "Poikkeus:",value
		
		self.MainWindow.set_title("SaunaVisio-aputyökalu v"+str(self.version)+" (v"+str(self.saunavisio_version)+")")

		self.SearchLabel = gtk.Label("Haku:")
		self.SearchEntry = gtk.Entry()
		self.SearchEntry.set_tooltip_text("Haussa voi käyttää tulosten rajaamiseen tuttuja ^, @ ja [] -yhdistelmiä.\nVain yhdellä hakulitanjalla hakeminen kerrallaan on mahdollista. ÄLÄ käytä lainausmerkkejä haun ympärillä.")
		self.SearchButton = gtk.Button("Hae")
		
		self.ButtonShowLatestRecordings =  gtk.Button("Uusimmat tallenteet")
		self.ButtonShowLatestRecordings.set_tooltip_text("Listaa tuoreimmat valmistuneet tallennukset. Ei välitä näkyvyyssäännöistä.")
		
		self.ButtonShowFuturePrograms = gtk.Button("Tulevat ohjelmat")
		self.ButtonShowFuturePrograms.set_tooltip_text("Listaa nyt menossa olevat ja tulevat ohjelmat vuorokauden ajalta noudattaen näkyvyyssääntöjä.")

		self.ButtonAddSearchword = gtk.Button("Lisää hakusana")
		self.ButtonAddSearchword.set_tooltip_text("Lisää yllä olevan kentän arvon uudeksi hakusanaksi. Hakusanojen filtteröinnissä voit käyttää ^-merkkejä hakusanan alussa ja lopussa katkaisemaan hakua. @-merkillä voit rajata kanavia: Monk@YLE TV1\n[]-merkeillä on mahdollista rajata hakusanalle tallennusväli: esim. [15-18] esittää kaikki hakusanaa vastaavat ohjelmat väliltä klo 15-18.")
		
		self.ButtonShowResultsForSearchwords = gtk.Button("Listaa")
		self.ButtonShowResultsForSearchwords.set_tooltip_text("Listaa hakusanojen mukaisesti kaikki ohjelmat noudattaen näkyvyyssääntöjä.")

		self.ButtonSetForRecording = gtk.Button("Tallenna")
		self.ButtonSetForRecording.set_tooltip_text("Asettaa hakusanojen perusteella ohjelmia tallennettavaksi noin viikon pituiselta ajanjaksolta.")

				
		self.SearchResultListStore = gtk.ListStore(str, str, str, str,str,str,str,str)
		self.SearchResultTreeModelSort = gtk.TreeModelSort(self.SearchResultListStore)
		
		
		self.SearchResultTreeView = gtk.TreeView(self.SearchResultListStore)
		#self.SearchResultTreeView = gtk.TreeView(self.SearchResultTreeModelSort)

		self.SearchResultTreeView.set_tooltip_markup("Tuplaklikkaamalla tallennettua ohjelmaa aloitat ohjelman toistamisen asetetulla videosoittimella.\n\nTuplaklikkaamalla ohjelmaa, jolle on asetettu tallennuspyyntö: tallennuspyyntö perutaan.\n\nTuplaklikkaamalla ohjelmaa, joka ei ole tallennettu tai jolle ei ole asetettu tallennuspyyntö: asetetaan ohjelma tallennettavaksi.\n\nHiiren oikea painike avaa popup-valikon.")

		self.SearchResultListStore.set_sort_column_id(SEARCHRESULT_COLUMN_DATE, gtk.SORT_DESCENDING)


		self.SearchResultTreeView.set_property("has-tooltip", True)
		self.SearchResultTreeView.set_headers_clickable(True)
		self.SearchResultTreeView.set_headers_visible(True)
		self.SearchResultTreeView.set_property("headers-clickable", True)
		
		# Asetetaan listaan monen rivin valinta käyttöön
		selection = self.SearchResultTreeView.get_selection()
		selection.set_mode(gtk.SELECTION_MULTIPLE)
		
		#.set_sort_column_id(n)
		
#		labels = ["ID", "Kanava", "Ajankohta", "Kesto", "Tila", "Nimi", "Kuvaus", "Color"]
#		for i in range(0,7):
#			print i
#			column = gtk.TreeViewColumn(labels[i], gtk.CellRendererText(), text=i, foreground=7)
#			column.set_sort_column_id(i)
#			self.SearchResultTreeView.append_column(column)
		
		self.SearchResultTreeView.append_column(gtk.TreeViewColumn('ID', gtk.CellRendererText(), text=SEARCHRESULT_COLUMN_ID, foreground=7))
		self.SearchResultTreeView.append_column(gtk.TreeViewColumn('Kanava', gtk.CellRendererText(), text=SEARCHRESULT_COLUMN_CHANNEL, foreground=7))
		self.SearchResultTreeView.append_column(gtk.TreeViewColumn('Ajankohta', gtk.CellRendererText(), text=SEARCHRESULT_COLUMN_DATE, foreground=7))
		self.SearchResultTreeView.append_column(gtk.TreeViewColumn('Tila', gtk.CellRendererText(), text=SEARCHRESULT_COLUMN_STATE, foreground=7))
		self.SearchResultTreeView.append_column(gtk.TreeViewColumn('Kesto', gtk.CellRendererText(), text=SEARCHRESULT_COLUMN_RUNTIME, foreground=7))
		self.SearchResultTreeView.append_column(gtk.TreeViewColumn('Nimi', gtk.CellRendererText(), text=SEARCHRESULT_COLUMN_NAME, foreground=7))
		self.SearchResultTreeView.append_column(gtk.TreeViewColumn('Kuvaus', gtk.CellRendererText(), text=SEARCHRESULT_COLUMN_DESCRIPTION, foreground=7))


		# Sorttausjärjestys yksiin ListStoren kanssa:
		columns = self.SearchResultTreeView.get_columns()
		columns[0].set_sort_column_id(0)
		columns[1].set_sort_column_id(1)
		columns[2].set_sort_column_id(2)
		columns[3].set_sort_column_id(6)
		columns[4].set_sort_column_id(3)
		columns[5].set_sort_column_id(4)
		columns[6].set_sort_column_id(5)
		#columns[7].set_sort_column_id(7)

#		# Rivin väriarvon sisältävä lohko piiloon... turha sitä on asettaakaan kun ei näytetä?
#		column = gtk.TreeViewColumn('Color', gtk.CellRendererText(), text=7)
#		column.set_visible(False)
#		self.SearchResultTreeView.append_column(column)

		#self.SearchResultListStore.set_sort_column_id(2,gtk.SORT_DESCENDING)

		
		self.SearchResultListStore.append(["12345","Kanava", "1.1.2008 12:34", "1h 30min", "Ohjelma","Kuvaus", "Tila", None])
		
		self.ScrolledWindowForTreeView = gtk.ScrolledWindow()
		self.ScrolledWindowForTreeView.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.ScrolledWindowForTreeView.add(self.SearchResultTreeView)


		self.StatusLabel = gtk.Label("Valmiina käyttöön: kirjoita Haku-kenttään hakutermi ja paina enter.")
		self.StatusLabel.set_justify(gtk.JUSTIFY_LEFT)
		
		#searchShowNew=True, searchShowRecorded=True, searchShowRequested=True
		self.SearchFilterLabel = gtk.Label("Näytä:")
		
		self.SearchRecordedCheckButton = gtk.CheckButton("Tallennetut")
		self.SearchNewCheckButton = gtk.CheckButton("Tallentamattomat")
		self.SearchRequestedCheckButton = gtk.CheckButton("Tallennuspyynnöt")
		self.SearchRecordedCheckButton.set_active(True)
		self.SearchNewCheckButton.set_active(True)
		self.SearchRequestedCheckButton.set_active(True)

		# Popup menu treeviewille
		self.PopupMenu = gtk.Menu()
		
		self.MenuItemPlay = gtk.MenuItem("Toista tallenne")
		self.MenuItemDownload = gtk.MenuItem("Lataa tallenteet")
		self.MenuItemRecord = gtk.MenuItem("Aseta tallennettavaksi")
		self.MenuItemRemove = gtk.MenuItem("Poista tallennuspyynnöt")
		self.MenuItemDelete = gtk.MenuItem("Tuhoa valitut")
		self.MenuItemFindMore = gtk.MenuItem("Hae lisää ohjelmia")


		self.MenuItemPlay.set_tooltip_text("Aloittaa valitun tallennetun ohjelman toistamisen videosoittimella")
		self.MenuItemDownload.set_tooltip_text("Avaa ohjelmien latausikkunan valituille ohjelmille")
		self.MenuItemRecord.set_tooltip_text("Asettaa kaikki valitut ohjelmat tallennettaviksi")
		self.MenuItemRemove.set_tooltip_text("Poistaa kaikilta valituilta ohjelmilta tallennuspyynnöt")
		self.MenuItemDelete.set_tooltip_text("Tuhoaa kaikki valitut tallennetut ohjelmat lopullisesti")
		self.MenuItemFindMore.set_tooltip_text("Hakee ensimmäisen valitun ohjelman nimellä lisää ohjelmia")
		
		
		self.PopupMenu.append(self.MenuItemPlay )
		self.PopupMenu.append(gtk.MenuItem() )
		self.PopupMenu.append(self.MenuItemFindMore )
		self.PopupMenu.append(self.MenuItemRecord )
		self.PopupMenu.append(self.MenuItemRemove )
		self.PopupMenu.append(self.MenuItemDelete )
		self.PopupMenu.append(gtk.MenuItem() )
		self.PopupMenu.append(self.MenuItemDownload )
		
		self.MenuItemPlay.connect("activate", self.MenuItem_activate_callback, "play")
		self.MenuItemRecord.connect("activate", self.MenuItem_activate_callback, "record")
		self.MenuItemRemove.connect("activate", self.MenuItem_activate_callback, "remove")
		self.MenuItemDelete.connect("activate", self.MenuItem_activate_callback, "delete")
		self.MenuItemDownload.connect("activate", self.MenuItem_activate_callback, "download")
		self.MenuItemFindMore.connect("activate", self.MenuItem_activate_callback, "findmore")
		
		
		self.PopupMenu.show_all()
		
		# MenuBar
		
		MenuBar = gtk.MenuBar()
		MenuBarItemEdit = gtk.MenuItem("Valinnat")
		MenuBar.add(MenuBarItemEdit)
		SubMenuEdit = gtk.Menu()
		MenuBarItemEdit.set_submenu(SubMenuEdit)
		MenuItemSettings = gtk.MenuItem("Asetukset")
		MenuItemNettiVisio = gtk.MenuItem("NettiVisio")
		SubMenuEdit.add(MenuItemNettiVisio)
		SubMenuEdit.add(gtk.MenuItem()) #Erotin
		SubMenuEdit.add(MenuItemSettings)

		SubMenuNettiVisio = gtk.Menu()
		MenuItemNettiVisio.set_submenu(SubMenuNettiVisio)
		
		for channel, url in self.saunavisio.channels:
			MenuItemNettiVisioChannel = gtk.MenuItem(channel)
			SubMenuNettiVisio.add(MenuItemNettiVisioChannel)
			MenuItemNettiVisioChannel.connect("button-release-event", self.MenuItemNettiVisioChannel_buttonreleaseevent_callback, channel)
			MenuItemNettiVisioChannel.set_tooltip_text("Aloita TV-kanavan "+channel+" katselu")

		MenuBarItemHelp = gtk.MenuItem("Apua")
		MenuBar.add(MenuBarItemHelp)
		SubMenuHelp = gtk.Menu()
		MenuBarItemHelp.set_submenu(SubMenuHelp)
		MenuItemInfo = gtk.MenuItem("Tietoa sovelluksesta")
		SubMenuHelp.add(MenuItemInfo)
		
		MenuItemInfo.connect("button-release-event", self.MenuItemInfo_buttonreleaseevent_callback)
		MenuItemSettings.connect("button-release-event", self.MenuItemSettings_buttonreleaseevent_callback)


		## Searchwords
		self.SearchwordsEntry = gtk.Entry()
		self.SearchwordsEntry.set_text("Hakusana...")
		
		self.SearchwordsListStore = gtk.ListStore(str)
		self.SearchwordsTreeView = gtk.TreeView(self.SearchwordsListStore)
		# Asetetaan solut hakusanalistassa muokattaviksi
		cell = gtk.CellRendererText()
		cell.set_property('editable', True)
		cell.connect("edited", self.SearchwordsColumnCell_edited_callback)
		self.SearchwordsTreeView.append_column(gtk.TreeViewColumn('Hakusanat', cell, text=0))
		self.SearchwordsTreeView.set_size_request(120,200)
		#self.SearchwordsListStore.append(["mo"])
		ScrolledWindowForTreeView = gtk.ScrolledWindow()
		ScrolledWindowForTreeView.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		ScrolledWindowForTreeView.add(self.SearchwordsTreeView)
		self.SearchwordsListStore.set_sort_column_id(0, gtk.SORT_ASCENDING)

		
		for sw in self.saunavisio.searchwords:
			self.SearchwordsListStore.append([sw])

		# Popup menu Searchwords:n treeviewille
		self.SearchwordsPopupMenu = gtk.Menu()
		
		self.SearchwordsMenuItemRemove = gtk.MenuItem("Poista hakusana")		
		
		self.SearchwordsPopupMenu.append(gtk.MenuItem() )
		self.SearchwordsPopupMenu.append(self.SearchwordsMenuItemRemove )
		
		self.SearchwordsMenuItemRemove.connect("activate", self.SearchwordsMenuItem_activate_callback)
		
		self.SearchwordsPopupMenu.show_all()
		
		
		# Kontainerit:			y,x
		#self.MainWindowTable = gtk.Table(4,4)
		self.SearchHBox = gtk.HBox()
		self.MainWindowVBox = gtk.VBox(False, 5)
		self.SearchFiltersHBox = gtk.HBox()
		self.HBoxSearchwordsAndTreeView = gtk.HBox()
		self.VBoxSearchwordsBase = gtk.VBox()
		
		# Palikkojen asettelu:
		self.MainWindow.add(self.MainWindowVBox)

		self.MainWindowVBox.pack_start(MenuBar, False, False, 2)

		self.SearchHBox.pack_start(self.SearchLabel, False, True, 10)
		self.SearchHBox.pack_start(self.SearchEntry)
		self.SearchHBox.pack_start(self.SearchButton, False, True)
		self.SearchHBox.pack_start(self.ButtonShowFuturePrograms, False, False, 3)
		self.SearchHBox.pack_start(self.ButtonShowLatestRecordings, False, False)
		
		self.MainWindowVBox.pack_start(self.SearchHBox, False)
		self.MainWindowVBox.pack_start(self.SearchFiltersHBox, False)
		self.MainWindowVBox.pack_start(self.HBoxSearchwordsAndTreeView)
		self.MainWindowVBox.pack_start(self.StatusLabel, False, True)

		self.HBoxSearchwordsAndTreeView.pack_start(self.VBoxSearchwordsBase, False, True, 2)
		self.HBoxSearchwordsAndTreeView.pack_start(self.ScrolledWindowForTreeView, True, True, 2)
				
		self.SearchFiltersHBox.pack_start(self.SearchFilterLabel)
		self.SearchFiltersHBox.pack_start(self.SearchNewCheckButton)
		self.SearchFiltersHBox.pack_start(self.SearchRequestedCheckButton)
		self.SearchFiltersHBox.pack_start(self.SearchRecordedCheckButton)

		self.VBoxSearchwordsBase.pack_start(ScrolledWindowForTreeView)
		self.VBoxSearchwordsBase.pack_start(self.SearchwordsEntry, False, False)
		self.VBoxSearchwordsBase.pack_start(self.ButtonAddSearchword, False, False)
		self.VBoxSearchwordsBase.pack_start(self.ButtonShowResultsForSearchwords, False, False, 3)
		self.VBoxSearchwordsBase.pack_start(self.ButtonSetForRecording, False, False)
		
		
		# Tapahtumat:
		self.MainWindow.connect("delete_event", self.MainWindow_close_callback)
		self.MainWindow.connect("destroy", self.MainWindow_destroy_callback)
		self.MainWindow.connect("key-press-event", self.MainWindow_keypressevent_callback)
		
		self.SearchEntry.connect("key-release-event", self.SearchEntry_keyreleaseevent_callback)
		self.SearchButton.connect("clicked", self.SearchButton_clicked_callback)

		self.SearchwordsEntry.connect("key-release-event", self.SearchwordsEntry_keyrelease_callback)

		self.SearchResultTreeView.connect("query-tooltip", self.SearchResultTreeView_quarytooltip_callback)
		self.SearchResultTreeView.connect("cursor-changed", self.SearchResultTreeView_cursorchanged_callback)
		# Pop-up menu
		self.SearchResultTreeView.connect("button-release-event", self.SearchResultTreeView_buttonreleaseevent_callback)
		# tallenteen suoratoisto
		self.SearchResultTreeView.connect("button-press-event", self.SearchResultTreeView_buttonpressevent_callback)

		self.SearchwordsTreeView.connect("button-press-event", self.SearchwordsTreeView_buttonpressevent_callback)		

		self.ButtonShowLatestRecordings.connect("clicked", self.ButtonShowLatestRecordings_clicked_callback)
		
		self.ButtonShowFuturePrograms.connect("clicked", self.ButtonShowFuturePrograms_clicked_callback)
		
		self.ButtonAddSearchword.connect("clicked", self.ButtonAddSearchwords_clicked_callback)
		self.ButtonShowResultsForSearchwords.connect("clicked", self.ButtonShowResultsForSearchwords_clicked_callback)
		self.ButtonSetForRecording.connect("clicked", self.ButtonSetForRecording_clicked_callback)
		
		# Alustetaan asetusikkuna
		self.Settings = self.SettingsDialog(self)

		# ja kaikki näkyville
		self.MainWindow.set_size_request(600,400)
		self.MainWindow.show_all()
		
		
		
		# Lista (tai paremminkin setti) ohjelma ID:stä, joille on jo aloitettu esikatselukuvan noutaminen
		self.NeverTwiceQuaryProgramThumbnailThreadSet = set()
		# Ja sama ohjelmatiedoille
		self.NeverTwiceQuaryProgramDetailsThreadSet = set()
		
		# Jos tyhjät conffit, heitetään asetusikkuna silmille
		if (self.saunavisio.firstRun):
			self.Settings.show()
			
			
		# Tarkistetaan sovellusta käynnistettäessä päivitysten saatavuus.
		if (self.saunavisio.doUpdateCheck):
			self.doUpdateCheck()
		
		# Lista latausikkunoista, käytetään tarkistamaan ettei latauksia ole suljettaessa pääikkunaa enää ajossa
		self.DownloaderDialogList = []
		

		# Ladataan asetustiedostosta mahdollisesti tallennetut näkyvyysasetukset, muuten True
		if (self.StoreVisibilitySettings):
			self.SearchNewCheckButton.set_active(bool(self.saunavisio.Config.get("SearchNewCheckButton")))
			self.SearchRequestedCheckButton.set_active(bool(self.saunavisio.Config.get("SearchRequestedCheckButton")))
			self.SearchRecordedCheckButton.set_active(bool(self.saunavisio.Config.get("SearchRecordedCheckButton")))
			
		
		return
		
	def doUpdateCheck(self):
		parent = self
		class UpdateCheckThread(threading.Thread):
			def __init__(self):
				threading.Thread.__init__(self)
				
				return	
			def run(self):
				new_cli_version=new_gui_version=0.0
				new_cli=False
				new_gui=False
				
				cli_data=gui_data=""
				print "Tarkistetaan päivityksiä..."
				message=""
				# Ensin saunavisio.py
				try:
					cli_handler = urllib2.urlopen("http://kapsi.fi/ighea/saunavisio/latest")
					data=cli_handler.read()
					cli_handler.close()
					new_cli_version=float(data[:data.find(" ")])
					if (parent.saunavisio.getVersion() < new_cli_version):
						print "Uusi saunavisio.py saatavilla: ", new_cli_version
						new_cli=True
					else:
						print "Ei päivitystä saunavisio.py:lle. Nykyinen:",parent.saunavisio.getVersion(),", tuorein:", new_cli_version
				except Exception, value:
					print value
					print "saunavisio.py:lle ei voitu noutaa tietoa päivityksistä."
					
				try:
					gui_handler = urllib2.urlopen("http://kapsi.fi/ighea/saunavisio/latest-gui")
					data=gui_handler.read()
					gui_handler.close()
					new_gui_version=float(data[:data.find(" ")])
					if (parent.version < new_gui_version):
						print "Uusi GUI.py saatavilla: ", new_gui_version
						new_gui=True
					else:
						print "Ei päivitystä GUI.py:lle. Nykyinen:",parent.version," tuorein:", new_gui_version
				except Exception, value:
					print value
					print "Gui.py:lle ei voitu noutaa tietoa päivityksistä."

				if (new_cli or new_gui):
					# uusi versio noudettavissa
					if (new_gui):
						message = message + "\nSaunaVisio GUI on päivitettävissä versioon <b>"+str(new_gui_version)+"</b>!"
						
					if (new_cli):
						message = message + "\nsaunavisio.py on päivitettävissä versioon <b>"+str(new_cli_version)+"</b>!"
					
					
					message=message+"\n\nUusimmat versiot löydät osoitteesta:\n\n <tt>http://kapsi.fi/ighea/saunavisio/</tt>"
					gtk.gdk.threads_enter()
					dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK, message_format=message)
					dialog.set_title("Päivityksiä saatavilla")
					dialog.set_markup(message)
					dialog.run()
					dialog.destroy()
					gtk.gdk.threads_leave()
				
				print "Valmis."
				return
				
		thread = UpdateCheckThread()
		thread.start()
		
		return


	def SearchwordsColumnCell_edited_callback(self, cellrenderertext, path, new_text):
		"""Päivittää solun muutokset hakusanalistaan ja tallentaa muutokset"""
		print path, new_text
		if (len(new_text) == 0):
			return
		iter = self.SearchwordsListStore.get_iter(path)
		old_text = self.SearchwordsListStore.get_value(iter, 0)
		# Poistetaan vanha hakusana
		self.saunavisio.delSearchWord(old_text)
		# Lisätään uusi hakusana:n
		self.saunavisio.addSearchWord(new_text)
		# Päivitetään muutos listaan
		self.SearchwordsListStore.set_value(iter, 0, new_text)
		print old_text, new_text
		# Tallennetaan muutokset
		self.saunavisio.saveSettings()
		return
		

	def ButtonSetForRecording_clicked_callback(self, widget):
		'''Painikkeen "Tallenna" tapahtuma "clicked", asettaa ohjelmat hakusanojen perusteella tallennettaviksi'''
	
		class MassRecorderThread(threading.Thread):
			'''Asettaa self.saunavisio.searchwords -hakusanojen perusteella ohjelmat tallennettaviksi'''
			def __init__(self, parent):
				threading.Thread.__init__(self)
				self.parent = parent
				
				return
			def run(self):
			
				try:
					searchdata = self.parent.saunavisio.getSearchData(self.parent.saunavisio.searchwords, False)
					progcount = float(len(searchdata))
					progcur = 0.0
			
					for program in searchdata:
						progcur+=1
						ID, kanava, aika, nimi, kuvaus, tila = program
						if (tila == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW):
							print "Tallennettavaksi: ", ID, " ", nimi
							self.parent.saunavisio.setToBeRecord(ID)
						gtk.gdk.threads_enter()
						percent = int(100*(progcur/progcount))
						self.parent.StatusLabel.set_label("Valmiina ohjelmien tallennettavaksi asettamisesta: "+str(percent)+" %")
						gtk.gdk.threads_leave()

				
					self.parent.showSearchResults(searchdata, searchShowNew=True, searchShowRequested=False, searchShowRecorded=False)
			
					gtk.gdk.threads_enter()
					iter = self.parent.SearchResultListStore.get_iter_first()
					while (iter != None):
						self.parent.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_COLOR, self.parent.searchResultColorRequested)
						self.parent.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_STATE, saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST)
						iter = self.parent.SearchResultListStore.iter_next(iter)
					
			
					self.parent.StatusLabel.set_label("Massatallennuspyynnöt asetettu, uudet tallennettaviksi merkatut näet hakulistasta.")
					self.parent.ButtonSetForRecording.set_sensitive(True)
					self.parent.SearchResultTreeView.columns_autosize()
					gtk.gdk.threads_leave()

				except Exception, value:
					eh = ExceptionHandler(value)
					eh.start()
					widget.set_sensitive(True)
		
				return
		## Luokka päättyy

		self.ButtonSetForRecording.set_sensitive(False)
		self.StatusLabel.set_label("Asetetaan ohjelmien tallennuspyyntöjä hakusanojen perusteella...")
			
		thread = MassRecorderThread(self)
		thread.start()
		return	
	
	
	def ButtonShowFuturePrograms_clicked_callback(self, widget):
		'''Esitä tulevat ohjelmat vuorokauden ajalta, painike'''
		class RunnerThread(threading.Thread):
			def __init__(self, parent):
				threading.Thread.__init__(self)
				self.parent = parent
				return
			def run(self):
				try:
					programData = self.parent.saunavisio.getFutureProgramsForNext24hours()
					self.parent.showSearchResults(programData, self.parent.SearchNewCheckButton.get_active(), self.parent.SearchRequestedCheckButton.get_active(), self.parent.SearchRecordedCheckButton.get_active())
				
					gtk.gdk.threads_enter()
					self.parent.StatusLabel.set_label("Ohjelmatiedot noudettu!")
				
					# Tuorein ensin
					self.parent.SearchResultListStore.set_sort_column_id(SEARCHRESULT_COLUMN_DATE, gtk.SORT_ASCENDING)
					widget.set_sensitive(True)
					gtk.gdk.threads_leave()
				except Exception, value:
					gtk.gdk.threads_leave()
					eh = ExceptionHandler(value)
					eh.start()
					widget.set_sensitive(True)
				
				return

		widget.set_sensitive(False)
		self.StatusLabel.set_label("Noudetaan ohjelmatietoja...")
						
		thread = RunnerThread(self)
		thread.start()
	
		return
		
	
	def ButtonShowResultsForSearchwords_clicked_callback(self, widget):
		'''Listaa hakusanojen perusteella ohjelmat'''
		self.StatusLabel.set_label("Haetaan ohjelmia hakusanojen perusteella...")

		self.doSearch(self.saunavisio.searchwords)	
	
		return
	
	
	def ButtonAddSearchwords_clicked_callback(self, widget):
		'''Asettaa Haku-kentän arvon uudeksi hakusanaksi'''
		searchword = self.SearchwordsEntry.get_text()
		if (len(searchword.strip()) < 1):
			self.StatusLabel.set_label("Tyhjää termiä ei lisätä hakusanaksi!")
			return
		
		# Lisätään hakusana listoihin
		self.saunavisio.addSearchWord(searchword)
		iter = self.SearchwordsListStore.append([searchword])
		# Scrollataan hakusanan paikkeille listalla
		self.SearchwordsTreeView.scroll_to_cell(self.SearchwordsListStore.get_path(iter))
		# Tyhjennetään hakusanan asetuskenttä
		self.SearchwordsEntry.set_text("")

		
	def MenuItemSettings_buttonreleaseevent_callback(self, widget, event):
		'''Näyttää Asetukset-ikkunan'''
		self.Settings.show()


	def MenuItemInfo_buttonreleaseevent_callback(self, widget, event):
		'''Näyttää "Tietoa sovelluksesta"-ikkunan'''
		dialog = gtk.AboutDialog()
		dialog.set_transient_for(self.MainWindow)
		try:
			dialog.set_logo(gtk.gdk.pixbuf_new_from_file("saunavisio.ico"))
		except Exception, value:
			print "Poikkeus:", value
		dialog.set_name("SaunaVisio-aputyökalu")
		dialog.set_version("v"+str(self.version))
		dialog.set_authors(['Mika "ighea" Hynnä <mika.hynna@wippies.com>'])
		dialog.set_comments("Sovellus tehokkaampaan SaunaVisio-palvelun ominaisuuksien hyödyntämiseen. Sovellus on lisensoitu GNU General Public Licence version 3 alaisena. Lisätietoja löydät tiedostosta LUEMINUT-GUI.txt. ")
		dialog.set_website("http://kapsi.fi/ighea/saunavisio/")
		dialog.set_program_name("SaunaVisio-aputyökalu")
		#dialog.set_logo()

		dialog.run()
		dialog.destroy()

	

	def MenuItemNettiVisioChannel_buttonreleaseevent_callback(self, widget, event, channel):
		try:
			self.StatusLabel.set_label("Aloitetaan videosoittimella kanavan toisto: "+channel)
			if (saunavisio.isWindowsOS()):
				gobject.idle_add(self.saunavisio.showTV, channel)
			else:
				self.saunavisio.showTV(channel)

		except Exception, value:
			eh = ExceptionHandler(value)
			eh.start()

	
	def ButtonShowLatestRecordings_clicked_callback(self, widget):
		'''Noutaa tiedot viimeisimmistä tallenteista ja esittää ne, painike'''
		self.ButtonShowLatestRecordings.set_sensitive(False)
		
		class ShowLatestRecordings(threading.Thread):
			def __init__(self, parent):
				threading.Thread.__init__(self)
				self.parent = parent
				
				return
			def run(self):
				try:
					latestrecordingsdata = self.parent.saunavisio.showLatestRecordings(False, False)
					self.parent.showSearchResults(latestrecordingsdata)
					self.parent.StatusLabel.set_label("Noudetaan viimeisimmät valmistuneet tallennukset... Valmis.")
					self.parent.ButtonShowLatestRecordings.set_sensitive(True)
					self.parent.SearchResultListStore.set_sort_column_id(SEARCHRESULT_COLUMN_DATE, gtk.SORT_DESCENDING)
				except Exception, value:
					eh = ExceptionHandler(value)
					eh.start()
					widget.set_sensitive(True)
				
				return
		
		try:
			print "Listataan viimeisimmät tallenteet"
			self.StatusLabel.set_label("Noudetaan viimeisimmät valmistuneet tallennukset...")
			thread = ShowLatestRecordings(self)
			thread.start()
		except Exception, value:
			print "Poikkeuksellinen poikkeus: ", value
		
		#finally:
		#	self.ButtonShowLatestRecordings.set_sensitive(True)
		
		
	def SearchwordsMenuItem_activate_callback(self, menuitem):
		'''Hakusanalistan popup-menun 'Poista'-valinta'''
		selection = self.SearchwordsTreeView.get_selection()
		model, paths = selection.get_selected_rows()
		for path in paths:
			iter = self.SearchwordsListStore.get_iter(path)
			hakusana = self.SearchwordsListStore.get_value(iter, 0)
			print "Poistetaan hakusana: "+hakusana
			self.saunavisio.delSearchWord(hakusana)
			self.SearchwordsListStore.remove(iter)
		
		return
	
	
	class ProgramStateChangerThread(threading.Thread):
		def __init__(self, parent, IDList, function, progressmessage="", donemessage="", *param):
			threading.Thread.__init__(self)
			self.IDList = IDList
			self.parent = parent
			self.function = function
			self.param = param
			self.progressmessage = progressmessage
			self.donemessage = donemessage
			return
			
		def run(self):
			try:
				print "Thread: Start"
				current=0.0
				count = float(len(self.IDList))
			
				for ID in self.IDList:
					if (len(self.param) > 0):
						self.function(ID, self.param)
					else:
						self.function(ID)
					if (self.progressmessage != ""):
						current+=1.0
						percent = int(100*(current/count))
						gtk.gdk.threads_enter()
						self.parent.StatusLabel.set_label(self.progressmessage+" "+str(percent)+" %")
						gtk.gdk.threads_leave()
		
				if (self.donemessage != ""):
					gtk.gdk.threads_enter()
					self.parent.StatusLabel.set_label(self.donemessage)
					gtk.gdk.threads_leave()
				print "Thread: End"
			except Exception, value:
				gtk.gdk.threads_leave()
				eh = ExceptionHandler(value)
				eh.start()
			return
	
		
	def MenuItem_activate_callback(self, menuitem, name):
		IDList = []
		selection = self.SearchResultTreeView.get_selection()
		model, paths = selection.get_selected_rows()
		print name
		print paths
		if (name == "record"):
			print "Asetetaan tallennettavaksi..."
			for path in paths:
				iter = self.SearchResultListStore.get_iter(path)
				tila = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_STATE)
				if (tila == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW):
					ID = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_ID)
					IDList.append(ID)
					self.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_STATE, saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST)
					self.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_COLOR, self.searchResultColorRequested)
								
				else:
					print "Ohjelma ei ole uusi"
			# Laitetaan threadi töihin:
			thread = self.ProgramStateChangerThread(self, IDList, self.saunavisio.setToBeRecord, "Valmiina ohjelmien tallennettavaksi asettamisesta:", "Valitut ohjelmat asetettu tallennettaviksi!")
			thread.start()
					
		elif (name == "remove"):
			print "Poistetaan tallennuspyyntöjä..."
			for path in paths:
				iter = self.SearchResultListStore.get_iter(path)
				tila = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_STATE)
				if (tila == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST):
					ID = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_ID)
					print ID
					IDList.append(ID)
					#result = self.saunavisio.cancelRecordingRequest([ID], False)
					#if (result==True):
					self.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_STATE, saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW)
					self.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_COLOR, self.searchResultColorNew)
				else:
					print "Ohjelma ei ole tallentumassa"
			# Laitetaan threadi töihin
			thread = self.ProgramStateChangerThread(self, IDList, self.saunavisio.cancelRecordingRequest, "Valmiina tallennuspyyntöjen poistosta:", "Valittujen ohjelmien tallennuspyynnöt poistettu!")
			thread.start()
			
		elif (name == "delete"):
			print "Tuhotaan tallenteet! ;D"
			dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Haluatko tuhota valitut tallenteet?\nToiminto on PERUUTTAMATON!")
			dialog.set_title("Tallenteiden tuhoaminen")
			resp = dialog.run()
			dialog.destroy()
			print resp
			if resp==gtk.RESPONSE_YES:
				print "yes"
			else:
				print "Toiminto peruttu"
				return

			destroy_iter_list = []
			for path in paths:
				iter = self.SearchResultListStore.get_iter(path)
				tila = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_STATE)
				if (tila == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED):
					ID = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_ID)
					print ID
					#result = self.saunavisio.destroyRecording(ID)
					#if (result==True):
					destroy_iter_list.append(iter)
					IDList.append(ID)
				else:
					print "Ohjelmaa ei ole tallennettu"

			thread = self.ProgramStateChangerThread(self, IDList, self.saunavisio.destroyRecording, "Valmiina valittujen tallenteiden tuhoamisesta:", "Valitut tallenteet tuhottu!")
			thread.start()

			print "Poistetaan tuhotut kohteet listasta:"
			for iter in destroy_iter_list:
				print self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_ID)
				self.SearchResultListStore.remove(iter)
			self.StatusLabel.set_label("Tuhottiin valitut tallenteet.")

	
		elif (name=="play"):
			print "Aloitetaan videon toisto.."
			for path in paths:
				iter = self.SearchResultListStore.get_iter(path)
				tila = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_STATE)
				nimi = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_NAME)
				if (tila == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED):
					# Jos levyllä olevien tallenteiden tarkistus on päällä ja tallenne löytyy levyltä
					# toistetaan se verkko-tiedoston sijaan
					kesto = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_RUNTIME)
					aika = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_DATE)
					filePath, fileName = self.saunavisio.filePathAndNameCreator(nimi, self.fromYYYYMMDDtoDDMMYYYY(aika), kesto)
					print filePath+fileName
					if (os.path.exists(filePath+fileName) and self.CheckStoredPrograms):
						print "Toistetaan video"
						self.saunavisio.playVideo(filePath+fileName)
					else:
						thread = self.PlayRecordThread(self, self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_ID))
						thread.start()
					break

		elif (name=="findmore"):
			print "Haetaan lisää ohjelmia.."
			for path in paths:
				iter = self.SearchResultListStore.get_iter(path)
				program = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_NAME)
				self.SearchEntry.set_text(program)
				print "program"
				break
			self.doSearch(program)

		elif (name == "download"):
			print "LArataan!!!! LArataan!!11"
			ohjelmalista=[]
			for path in paths:
				iter = self.SearchResultListStore.get_iter(path)
				tila = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_STATE)
				if (tila == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED):
					ID = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_ID)
					kanava = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_CHANNEL)
					aika = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_DATE)
					ohjelma = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_NAME)
					kuvaus = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_DESCRIPTION)
					tila = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_STATE)
					ohjelmalista.append([ID,kanava,aika,ohjelma,kuvaus])
			if (len(ohjelmalista) > 0):
				print ohjelmalista
				#self.programDownloader.show(ohjelmalista)
				programDownloader = self.DownloaderDialog(self)
				programDownloader.show(ohjelmalista)
				# Lisätään akkuna tarkistuslistalle
				self.DownloaderDialogList.append(programDownloader)


	class PlayRecordThread(threading.Thread):
		def __init__(self, parent, ID):
			threading.Thread.__init__(self)
			self.parent = parent
			self.ID = ID
			print "PlayRecordThread created!"
			return
			
		def run(self):
			print "PlayRecordThread start!"
			try:
				self.parent.saunavisio.playRecord(self.ID)
			except Exception, value:
				print value
				message, exitcode = value
				print "ek", exitcode
				# Suoritettavaa ohjelmaa ei löytynyt:
				if (exitcode == 32512):
					gtk.gdk.threads_enter()
					dialog = gtk.MessageDialog(parent=self.parent.MainWindow, flags=0, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format=str(message))
					dialog.set_title("Virhe toistettaessa tallennetta")
					resp = dialog.run()
					dialog.destroy()
					gtk.gdk.threads_leave()
			print "PlayRecordThread stop!"
			return

	
	def SearchwordsTreeView_buttonpressevent_callback(self, widget, event):
		# Hiiren vasenkorva
		if (event.button == 1):
			sel = self.SearchwordsTreeView.get_selection()
			model, paths = sel.get_selected_rows()
			# Tuplaclikkaus laittaa hakusanan hakukenttään ja suorittaa haun..
			if (event.type == gtk.gdk._2BUTTON_PRESS):
				for path in paths:
					iter = self.SearchwordsListStore.get_iter(path)
					hakusana = self.SearchwordsListStore.get_value(iter, 0)
					self.SearchEntry.set_text(hakusana)
					self.doSearch()
				return
		# Hiirun oikea korva
		elif (event.button == 3):
			self.SearchwordsPopupMenu.popup(None,None,None,0,0)
			return

	
		
	def SearchResultTreeView_buttonreleaseevent_callback(self, widget, event):
		# Hiiren oikea korva vapautettu, PopUp-menu esiin:
		if (event.button == 3):
			self.PopupMenu.popup(None,None,None,0,0)


	def SearchResultTreeView_buttonpressevent_callback(self, widget, event):
		#print event.button
		#print event.type
		# Vasen hiirenkorva
		if (event.button == 1):
			# Tuplaclickaus, aloitetaan videon toisto jos tallenne on valmis
			if (event.type == gtk.gdk._2BUTTON_PRESS):
				sel = self.SearchResultTreeView.get_selection()
				model, paths = sel.get_selected_rows()
				for path in paths:
					iter = self.SearchResultListStore.get_iter(path)
					ID = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_ID)
					tila = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_STATE)
					# Aloitetaan tallenteen toisto
					if (tila == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED):
						kesto = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_RUNTIME)
						aika = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_DATE)
						nimi = self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_NAME)
						filePath, fileName = self.saunavisio.filePathAndNameCreator(nimi, self.fromYYYYMMDDtoDDMMYYYY(aika), kesto)
						print filePath+fileName
						# Jos tallenne löytyy levyltä ja tallenteen levyllä olevien tallenteiden näyttäminen on
						# käytössä aloitetaan tallenteen toisto paikallisesti verkon sijaan
						if (os.path.exists(filePath+fileName) and self.CheckStoredPrograms):
							print "Toistetaan video"
							self.saunavisio.playVideo(filePath+fileName)
						else:
							self.StatusLabel.set_text("Aloitetaan tallenteen toisto...")
							#self.saunavisio.playRecord(ID)
							thread= self.PlayRecordThread(self, ID)
							thread.start()
						break
					# Tallennettavana, poistetaan tallennuspyyntö
					elif (tila == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST):
						self.StatusLabel.set_text("Perutaan yksittäinen tallennuspyyntö...")
						result = self.saunavisio.cancelRecordingRequest([ID], False)
						if (result==True):
							self.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_STATE, saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW)
							self.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_COLOR, self.searchResultColorNew)
						break
					elif (tila == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW):
					# Asetetaan tallennettavaksi
						self.StatusLabel.set_text("Asetetaan yksittäinen tallennuspyyntö...")
						result = self.saunavisio.setToBeRecord(ID)
						if (result==True):
							self.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_STATE, saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST)
							self.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_COLOR ,self.searchResultColorRequested)
						break
						
				return


		
	def SearchResultTreeView_cursorchanged_callback(self, widget):
		#gtk.tooltip_trigger_tooltip_query(gtk.gdk.display_get_default())
		#print "cursor-changed"
		True
	
	
	class QuaryProgramThumbnailThread(threading.Thread):
		def __init__(self, parent, ID, showData=""):
			threading.Thread.__init__(self)
			self.parent = parent
			self.ID = ID
			self.showData=showData
			self.setName="QuaryProgramThumbnailThread:"+showData
		
			return
		
		def run(self):
			try:
				print "Noudetaan esikatselukuvaa: "+ self.ID
		
				if (not os.path.exists(self.parent.saunavisio.configdirectory + "thumbnails")):
					os.mkdir(self.parent.saunavisio.configdirectory + "thumbnails")
				imagefile = self.parent.saunavisio.configdirectory + "thumbnails" + os.path.sep+ self.ID + ".jpg"

				imagedata = self.parent.saunavisio.openURL("http://tvmedia10.saunalahti.fi/thumbnails/"+self.ID+".jpg")
				
				if (imagedata != ""):
					f = open(imagefile,"w")
					f.write(imagedata)
					f.flush()
					f.close()

					print "Esikatselukuva noudettu ja talletettu: "+ self.ID
				else:
					print "Ei dataa kohteelle: ", self.ID
			except Exception, value:
				f.close()
				print "Poikkeus:", value
		
			return
	
	
	class QuaryProgramInfoThread(threading.Thread):
		'''Noutaa ohjelman kuvauksen ja keston sekä asettaa tiedot paikoilleen'''
		def __init__(self, parent, ID, showData=""):
			threading.Thread.__init__(self)
			self.setName("QuaryProgramInfoThread:"+showData)
			# Ohjelman ID, jonka tietoja noudetaan
			self.ID = ID
			# Threadiä ajava luokka:
			self.parent = parent
			
			self.showData = showData
			
		def run(self):
			try:
				kuvaus=kesto=""
				print "Noudetaan kuvausta ohjelmalle: "+self.showData
				gtk.gdk.threads_enter()
				self.parent.StatusLabel.set_label("Haetaan ohjelmatietoja... "+self.showData)
				gtk.gdk.threads_leave()
		
				# Noudetaan ohjelmatiedot webistä:
				durl, id, nimi, aika, kesto, wgetcmd, kuvaus, destFilePath, destFileName = self.parent.saunavisio.fetchDownloadUrl(self.ID, verbose=False)
				
				gtk.gdk.threads_enter()
				
				iter = self.parent.SearchResultListStore.get_iter_first()
				while (iter != None):
					if (self.ID == self.parent.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_ID)):
						self.parent.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_DESCRIPTION, kuvaus)
						self.parent.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_RUNTIME, kesto)
						break
					else:
						iter = self.parent.SearchResultListStore.iter_next(iter)
			
				self.parent.StatusLabel.set_label("Ohjelmatiedot noudettu!")

				# Jos ohjelma on tallennettu ja ladattu tiedosto löytyy levyltä edes osittain
				# värjätään eri sävyllä
				if (self.parent.CheckStoredPrograms == True):
					if (self.parent.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_STATE) == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED):
						destFilePath, destFileName = self.parent.saunavisio.filePathAndNameCreator(nimi, aika, kesto)
						if (os.path.exists(destFilePath+destFileName)):
							self.parent.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_COLOR, self.parent.searchResultColorOndisk)

				gtk.gdk.threads_leave()

				# Lopuksi lisätään kuvaus ja kesto tietokantaan
				self.parent.idDictionary.append(self.ID, (kuvaus, kesto) )
				print "Kuvaus noudettu: "+self.showData

			except Exception, value:
				gtk.gdk.threads_leave()
				print "Poikkeus: ", value
			return
		

	def SearchResultTreeView_quarytooltip_callback(self, widget, x, y, keyboard_mode, tooltip):
		kuvaus="" #Ohjelman kuvaus
		kesto=""  #Ohjelman kesto
		try:
			path = self.SearchResultTreeView.get_dest_row_at_pos(x, y)
		except TypeError:
			return False
		
		# ollaan olemassaolevan rivin yllä hiirellä
		if (path != None):
			iter = self.SearchResultListStore.get_iter(path[0])
			kuvaus=self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_DESCRIPTION)
			ID = self.SearchResultListStore.get_value(iter,SEARCHRESULT_COLUMN_ID)
			ohjelma = self.SearchResultListStore.get_value(iter,SEARCHRESULT_COLUMN_NAME)
			aika = self.SearchResultListStore.get_value(iter,SEARCHRESULT_COLUMN_DATE)
			kesto = self.SearchResultListStore.get_value(iter,SEARCHRESULT_COLUMN_RUNTIME)
			kanava = self.SearchResultListStore.get_value(iter,SEARCHRESULT_COLUMN_CHANNEL)
			
			# Noudetaan ohjelmalle kuvaus ja kesto
			
			
			if (len(kuvaus) < 2 or len(kesto) < 2):
				try:
					kuvaus, kesto = self.idDictionary.find(ID)
				except KeyError, value:
					print "KeyError:",value
					if (not ID in self.NeverTwiceQuaryProgramDetailsThreadSet):
						# Noudetaan threadillä ohjelmalle kuvaus ja kesto
						thread = self.QuaryProgramInfoThread(self, ID, ohjelma)
						thread.start()

			# Jost edelleen tietokannasta huolimatta kuvaus tai aika puuttuu, koitetaan noutaa tieto
			if (len(kuvaus) < 2 or len(kesto) < 2):
				if(not ID in self.NeverTwiceQuaryProgramDetailsThreadSet):
					self.NeverTwiceQuaryProgramDetailsThreadSet.add(ID)
					# Noudetaan threadillä ohjelmalle kuvaus ja kesto
					thread = self.QuaryProgramInfoThread(self, ID, ohjelma)
					thread.start()
								
			
			# Näytetään ja haetaan esikatselukuvajaiset tallenteille
			if (self.ShowThumbnails):
				if (self.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_STATE) == saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED):
					if (not os.path.exists(self.saunavisio.configdirectory + "thumbnails")):
						os.mkdir(self.saunavisio.configdirectory + "thumbnails")
					imagefile = self.saunavisio.configdirectory + "thumbnails" + os.path.sep+ ID + ".jpg"

					if (not os.path.exists(imagefile)):
						if(not ID in self.NeverTwiceQuaryProgramThumbnailThreadSet):
							self.NeverTwiceQuaryProgramThumbnailThreadSet.add(ID)
							try:
								thread = self.QuaryProgramThumbnailThread(self, ID, ohjelma)
								thread.start()
							except IOError,value:
								print "Virhe kirjoitettaessa levylle! Levy täysi?\nIOError:", value

					else:
						# Kuva on olemassa, pannaan laraten ja asettaen
						try:
							tooltip.set_icon(gtk.gdk.pixbuf_new_from_file(imagefile))
						except Exception, value:
							print "Poikkeus asetettaessa esikatselukuvaa:", value
			
			if (len(kuvaus) < 2):
				#print "kohteen tietoja ei voitu noutaa?"
				kuvaus="Ei ohjelmatietoja saatavilla."
				self.SearchResultListStore.set(iter, SEARCHRESULT_COLUMN_DESCRIPTION, kuvaus)
			
			tooltip.set_markup("<b>"+ohjelma.replace("&","&amp;")+"</b> ("+aika+") "+kanava+"\nKesto: "+kesto+"\n\n"+kuvaus.replace("&","&amp;"))
			
			return True
		return False
		

	# Esittää ruksia/sulkemistapahtumia
	def MainWindow_close_callback(self, widget,event):
		stillDownloading = False
		
		for dd in self.DownloaderDialogList:
			print "item"
			if (dd.downloading):
				print "downloading"
				stillDownloading=True
		
		if (stillDownloading):
			dialog = gtk.MessageDialog(parent=self.MainWindow, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Tallenteiden latauksia on yhä käynnissä!\n\nHaluatko varmasti sulkea sovelluksen nyt?")
			dialog.set_title("Varmistus")
			resp = dialog.run()
			dialog.destroy()
			print resp
			if resp==gtk.RESPONSE_YES:
				print "yes"
			else:
				print "Toiminto peruttu, ei suljeta ikkunaa"
				return True
		
		print self.StoreVisibilitySettings
		if (self.StoreVisibilitySettings):
			print "Tallennetan näkyvyysasetukset.."
			self.saunavisio.Config.set("SearchNewCheckButton", self.SearchNewCheckButton.get_active())
			self.saunavisio.Config.set("SearchRequestedCheckButton", self.SearchRequestedCheckButton.get_active())
			self.saunavisio.Config.set("SearchRecordedCheckButton", self.SearchRecordedCheckButton.get_active())
			self.saunavisio.saveSettings()
			
		if (stillDownloading):
			for dd in self.DownloaderDialogList:
				dd.downloadThread.die()
			print "Nyt tullee kolinalla alas, HIH! :P, odotetaan sekka."
			time.sleep(1)

		print "Suljetaan sovellus..."		
		#self.DownloaderDialogList
		return False


	# Ikkunan sulkeutuessa lopetetaan GTK:n pääloopin ajo ja koko sovellus
	def MainWindow_destroy_callback(self, widget):
		self.idDictionary.save()
		gtk.main_quit()
		print "\n"
		sys.exit()
		return
	
	def gtk_main(self):
		'''Käynnistetään GTK:n pää-looppi eli käynnistetään itse sovellus.'''
		gtk.main()
		return

				
	def doSearch(self, searchwords=None):
		self.thread_count+=1
		self.StatusLabel.set_text("Haetaan tietoja...")
		
		if (searchwords == None):
			# Ei hakusanoja?
			if (len(self.SearchEntry.get_text()) > 0):
				threadi = self.SearchRunner(self, [self.SearchEntry.get_text()], self.thread_count)
			else:
				self.StatusLabel.set_label("Haku-kenttä tyhjä, ei haeta!")
				# Haku-kenttä tyhjä, ei haeta!
				return
		else:
			if (not type(searchwords) == list):
				searchwords=[searchwords]
			threadi = self.SearchRunner(self, searchwords, self.thread_count)
		
		threadi.start()
			
		print "#"+str(self.thread_count)+", Done."


	def SearchButton_clicked_callback(self, widget):
		self.SearchResultListStore.clear()
		self.doSearch()
	
	
	def MainWindow_keypressevent_callback(self, widget, event):
		if (event.type == gtk.gdk.KEY_PRESS):
			if (event.state == gtk.gdk.CONTROL_MASK):
				print event.keyval
				print event.hardware_keycode
				if (event.keyval == 108): # L
					self.SearchEntry.grab_focus()
				if (event.keyval == 107): # K
					self.SearchwordsEntry.grab_focus()
					
		
		return
	
	
	def SearchwordsEntry_keyrelease_callback(self, widget, event):
		'''Hakusanan lisäyskentän näppäimistöpainallusten käsittelijä'''
		# Painettiin entteriä:
		if (event.keyval == 65293):
			'''Asettaa Haku-kentän arvon uudeksi hakusanaksi'''
			searchword = self.SearchwordsEntry.get_text()
			if (len(searchword.strip()) < 1):
				self.StatusLabel.set_label("Tyhjää termiä ei lisätä hakusanaksi!")
				return
		
			# Lisätään uusi hakusana sekä ruudulle että hakusanalistaan
			self.saunavisio.addSearchWord(searchword)
			iter = self.SearchwordsListStore.append([searchword])
			# Scrollataan asetetun sakuhanan kohtiille
			self.SearchwordsTreeView.scroll_to_cell(self.SearchwordsListStore.get_path(iter))
			# Lopuksi tyhjennetään hakusanan lisäyskenttä
			self.SearchwordsEntry.set_text("")
			
		return

	
	def SearchEntry_keyreleaseevent_callback(self, widget, event):
		# Painettiin entteriä:
		if (event.keyval == 65293):
			self.doSearch()		
		return
		
		
	def showSearchResults(self, programList, searchShowNew=True, searchShowRequested=True, searchShowRecorded=True):
		'''Listaa programList-listan sisällön SearchResultTreeView:ssä, asettaa värikoodaukset.'''
		# Tyhjennetään ohjelmalista

		self.SearchResultListStore.clear()

		# Tyhjennetään noudetuista esikatselukuvista ja kuvauksista hakulistausta kohden kirjaa pitävä lista... SETti ;)
		self.NeverTwiceQuaryProgramThumbnailThreadSet = set()	
		self.NeverTwiceQuaryProgramDetailsThreadSet = set()	


		for ohjelma in programList:
			ID, kanava, aika, nimi, kuvaus, tila = ohjelma

			# Erotetaan uusimpien tallenteiden listauksesta aika ja kesto
			aikaerotin = aika.find("/")
			if (aikaerotin != -1):
				kesto = aika[aikaerotin+1:].strip()
				aika = aika[:aikaerotin].strip() 
			else:
				kesto=""
			

			color=None
			# Lyödään filtteröidyt hakutulokset taulukkoon ja väritellään mukavasti tilan perusteella
			if (tila==saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW and searchShowNew==True or tila==saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED and searchShowRecorded==True or tila==saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST and searchShowRequested==True):
				if (tila==saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW):
					color=self.searchResultColorNew
				elif (tila==saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST):
					color=self.searchResultColorRequested
				elif (tila==saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED):
					color=self.searchResultColorRecorded

				# Lisätään tunnetut kuvaukset suoraan
				try:
					(kuvaus, kesto) = self.idDictionary.find(ID)
				except KeyError, value:
					print "Kuvausta ei löytynyt ohjelmalle ", value
					if (len(kuvaus) > 2):
						self.idDictionary.append(ID, (kuvaus, kesto))

				# Jos tallenne löytyy myös levyltä, värjätään se eri sävyllä
				if (self.CheckStoredPrograms == True):
					if (tila==saunavisio.SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED):
						destFilePath, destFileName = self.saunavisio.filePathAndNameCreator(nimi, aika, kesto)
						if (os.path.exists(destFilePath+destFileName)):
							color=self.searchResultColorOndisk

				# Heitetään aika muodosta "dd.mm.yyyy HH:MM" muotoon "yyyy.mm.dd HH:MM"
				aika = self.fromDDMMYYYYtoYYYYMMDD(aika)

				
				path_newrow = self.SearchResultListStore.insert(0, [ID,kanava,aika,kesto,nimi,kuvaus,tila, color])
				
				#print path_newrow
		if (len(programList) < 1):
			self.StatusLabel.set_label("Haulla ei löytynyt tuloksia!")
			

		self.SearchResultTreeView.columns_autosize()
		
		if (len(self.SearchResultListStore) > 0):
			self.SearchResultTreeView.scroll_to_cell((0,), self.SearchResultTreeView.get_column(0), use_align=False, row_align=0.0, col_align=0.0)

		# Automaattinen ohjelmatietojen nouto, käynnistyy kun ohjelmatiedot on saatu listattua SearchResultTreeView:in
		if (self.AutoFetchProgramInfo):
			print "Automaattinen ohjelmatietojen nouto käytössä."
			class ProgramInfoFetcherThread(threading.Thread):
				def __init__(self, parent):
					threading.Thread.__init__(self)
					self.parent = parent
					self.running = True
					self.listcount = len(self.parent.SearchResultListStore)
					return
				def run(self):
					time.sleep(0.5)
					iter = self.parent.SearchResultListStore.get_iter_first()
					while (iter != None and self.running and self.listcount == len(self.parent.SearchResultListStore)):
						ID = self.parent.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_ID)
						kesto = self.parent.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_RUNTIME)
						kuvaus = self.parent.SearchResultListStore.get_value(iter,SEARCHRESULT_COLUMN_DESCRIPTION)
						nimi = self.parent.SearchResultListStore.get_value(iter, SEARCHRESULT_COLUMN_NAME)
						if (len(kuvaus) < 2 or len(kesto) < 2 ):
							if(not ID in self.parent.NeverTwiceQuaryProgramDetailsThreadSet):
								self.parent.NeverTwiceQuaryProgramDetailsThreadSet.add(ID)
								# Noudetaan threadillä ohjelmalle kuvaus ja kesto
								thread = self.parent.QuaryProgramInfoThread(self.parent, ID, nimi)
								thread.start()
								# Noudetaanko "kerralla" vai yksitellen, kas siinä pulma...
								thread.join()
						if (not self.running or self.listcount != len(self.parent.SearchResultListStore)):
							return
						iter = self.parent.SearchResultListStore.iter_next(iter)
				
					return
			AutoFetchThread = ProgramInfoFetcherThread(self)
			AutoFetchThread.start()
			
		return True


	def fromDDMMYYYYtoYYYYMMDD(self, aika):
		'''Muuntaa muotoa DD.MM.YYYY HH:mm ajan muotoon YYYY.MM.YYYY HH:mm'''
		aika=aika.strip()
		# Todennäköisesti aika on väärässä muodossa, palautetaan mitä saatiinkin
		if (aika[2] != "."):
			return aika
		y = aika[aika.rfind(".")+1:aika.rfind(".")+5]
		m = aika[3:5]
		d = aika[:2]
		k = aika[-5:]
		aika = y+"."+m+"."+d+" "+k
		return aika

	def fromYYYYMMDDtoDDMMYYYY(self, aika):
		'''Muuntaa muotoa YYYY.MM.YYYY HH:mm ajan muotoon DD.MM.YYYY HH:mm'''
		aika=aika.strip()
		# Todennäköisesti aika on väärässä muodossa, palautetaan mitä saatiinkin
		if (aika[2] == "."):
			return aika
		y = aika[:4]
		m = aika[5:7]
		d = aika[8:10]
		k = aika[-5:]
		aika = d+"."+m+"."+y+" "+k
		return aika



# Sovellusta suoritetaan suoraan:
if __name__ == "__main__":
	gui = GUI()
	gui.gtk_main()
	
# Tulostetaan aina tyhjä rivi
print "\n"
