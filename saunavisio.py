#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# * This program is free software. It comes without any warranty, to
# * the extent permitted by applicable law. You can redistribute it
# * and/or modify it under the terms of the Do What The Fuck You Want
# * To Public License, Version 2, as published by Sam Hocevar. See
# * http://sam.zoy.org/wtfpl/COPYING for more details. */ 
 
import os, sys, cookielib, socket, urllib2, time, random, threading

# Vakiot "tila" -muuttujille
SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW = "Ohjelm"
SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST = "Pyyntö"
SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED = "Valmis"


def isWindowsOS():
	'''Tarpeeksi pätevä Windowssin tunnistus...?'''
	if ("win" in sys.platform):
		return True
	else:
		return False


class Config:
	def __init__(self, configfile=None):
		self.configfile=configfile
		self.configfiledata=""
		self.changesNotSaved=False

		if (isWindowsOS()):
			defaultplayer = "C:\Program Files\VideoLAN\VLC\VLC.exe"
		else:
			defaultplayer = "vlc --sub-language Suomi --deinterlace-mode x"

		self.template = [
			["username",""],
			["password",""],
			["searchwords",'["Simpsonit","Salatut elämät","Monk@YLE TV1"]'],
			["videoplayer", defaultplayer],
			["doupdatecheck","True"],
			["downloaddirectory",os.path.expanduser("~")],
			["downloadUseSubDirs","False"],
			["showthumbnails","True"]
			]

		return
	
	def __create_config(self):
		self.configfiledata = ""
		for value, data in self.template:
			self.configfiledata = self.configfiledata + value+ '=' + data + os.linesep	
	
		self.save()
		return True
	
	def isChanged(self):
		return self.changesNotSaved
	
	# Palauttaa joko arvon (str, bool tai list, tyypistä riippuen) tai None
	#
	def get(self, value, value_type=None):
		'''Noutaa value-avaimen arvon tiedostosta, käärii sen haluttaessa value_type:n läpi.'''
		# Liikaa häviötä None-objektilla
		data=""
		for line in self.configfiledata.split(os.linesep):
			sep = line.find('=')
			if (sep != -1):
				testvalue = line[:sep]
				#print testvalue, value
				if (testvalue == value):
					data=line[sep+1 : ]
					if ("[" in data and "]" in data):
						data=eval(data) # Muutetaan listaksi
					elif (data == "True"):
						data = True
					elif (data == "False"):
						data = False
					elif (data == None):
						data = False
					if (value_type != None):
						data = value_type(data)
					#print "GET:", value, data
					return data
		
		# Ei löydetty arvoa tiedostosta, tarkistetaan template ja palautetaan löytyessä defaultti		
		for templatevalue, data in self.template:
			if (value == templatevalue):
				if ("[" in data and "]" in data):
					data=eval(data) # Muutetaan listaksi
				elif (data == "True"):
					data = True
				elif (data == "False"):
					data = False
				elif (data == "None"):
					data = False
				if (value_type != None):
					data = value_type(data)
				#print "GET:", value, data
				return data
		
		# Käärästään lopuksi 'data' halutun tietotyypin läpi
		if (value_type != None):
			data = value_type(data)
		#print "GET:", value, data
		
		return data

	
	# Asettaa arvoja, korjaa jos ongelmia ilmenee
	def set(self, value, data):
		# vamistuksena =-merkki
		valuepos = self.configfiledata.find( str(value) + "=" )
		if (valuepos != -1):
			tmp_start_data = self.configfiledata[:valuepos]
			line_end = self.configfiledata.find(os.linesep, valuepos)
			tmp_end_data = self.configfiledata[line_end:]
			self.configfiledata = tmp_start_data + str(value) + "=" + str(data)+ tmp_end_data 
			
			return	

		# Ei löytynyt arvoa, lisätään
		if (self.configfiledata[:-1] == os.linesep):
			self.configfiledata = self.configfiledata + str(value) + "=" + str(data) + os.linesep
		else:
			self.configfiledata = self.configfiledata + os.linesep + str(value) + "=" + str(data) + os.linesep
		
		self.changesNotSaved = True

		return

			
	def load(self):
		# Jos asetustiedosto ei ole ennestään olemassa luodaan pohja
		if (not os.path.exists(self.configfile)):
			self.__create_config()
			
		# Luetaan asetustiedosto
		try:
			f = open(self.configfile, "r")
			self.configfiledata = f.read()
			f.close()
		except IOError, value:
			print "Virhe: ", value
			return False
		
		self.changesNotSaved=True
		#print self.configfiledata
		return True
		
	def save(self):
		confdir = os.path.dirname(self.configfile)
		if (not os.path.exists(confdir)):
			print "Config: Hakemistoa asetustiedostoille ei ole olemassa."
			print "Config: Luodaan: "+ confdir
			print "Tallennetaan asetustiedostopohja hakemistoon"
			os.mkdir(confdir)
		
		# Lisätään tiedoston alkuun tyhjä rivi
		if (not self.configfiledata.startswith(os.linesep)):
			self.configfiledata = os.linesep + self.configfiledata
		
		#Tallennetaan asetustiedosto
		try:
			f = open(self.configfile, "w")
			f.write(self.configfiledata)
			f.flush()
			f.close()
		except IOError, value:
			print "Virhe: ", value
			return False
		#print self.configfiledata
		self.changesNotSaved=False
		return True		

########### Config-luokka päättyy  ##########


class SaunaVisio:
	'''SaunaVisio:n hallinta-luokka'''
	def __init__(self):
		self.versio=0.994

		self.username=""
		self.password=""
		self.videoplayer="vlc --sub-language Suomi --deinterlace-mode x"

		self.searchwords=['Smallville', 'Simpsonit', 'Elokuva']
		self.doUpdateCheck=True

		self.downloaddirectory=""
		self.downloadUseSubDirs=False

		self.paranoiaMode=False
		self.dorecording=False
		
		self.firstRun = False
		
		
		self.urlRequestTimeout = 10
		socket.setdefaulttimeout(self.urlRequestTimeout)
		
		# Asetustiedostot:
		if (isWindowsOS()):
			# Luulee olevansa windowssi
			self.configdirectory = os.path.expanduser("~") + os.path.sep + "Saunavisio"+os.path.sep
			self.configfile = self.configdirectory+"saunavisio.conf"
		else:
			# Muut:
			self.configdirectory = os.path.expanduser("~") + os.path.sep + ".saunavisio"+os.path.sep
			self.configfile = self.configdirectory+"saunavisio.conf"


		# Ajetaan tyhjiltä conffeilta
		if (not os.path.exists(self.configfile)):
			self.firstRun = True
		
		self.Config = Config(self.configfile)
		
		# NettiVision kanavat:
		self.channels = [["YLE TV1", "http://195.197.55.188:8000/"],["YLE TV2", "http://195.197.55.188:8001/"],["MTV3", "http://195.197.55.188:8005/"],["Nelonen", "http://195.197.55.188:8007/"],["YLE FST5", "http://195.197.55.188:8004/"],["Sub", "http://195.197.55.188:8006/"],["Urheilukanava", "http://195.197.55.188:8009/"],["YLE Extra", "http://195.197.55.188:8002/"],["YLE Teema", "http://195.197.55.188:8003/"],["The Voice", "http://195.197.55.188:8010/"],["JIM", "http://195.197.55.188:8008/"]]

		#self.searchShowNew = self.searchShowRecorded = self.searchShowRequested = True

		self.reloginRetrys=3 # Käytetään openURL:ssa uudelleenkirjautumisiin
		self.isLoginSuccess=False
		# Aika jolloin kirjautuminen viimeksi onnistui
		self.lastLoginTime=time.time()
	
		# Luodaan cookieJar
		self.cookieJar = cookielib.CookieJar()
		random.seed()

		print "\n>>> SaunaVisio aputyökalu v"+str(self.getVersion())+" <<<\n"
		print "*** Purkannut Mika Hynnä <mika.hynna@wippies.com> ***\n"
		print "*** Lisensoitu WTFPL:n alaisena, lisätietoja osoitteesta:"
		print "*** http://sam.zoy.org/wtfpl/COPYING\n"

		return
		

	def getVersion(self):
		return float(self.versio)


	def checkForUpdate(self, doUpgrade=False, silentUpgrade=False):

		# Jos päivitysten tarkistus on kytketty pois päältä ja käskyä "päivitä" ei ole annettu: ei tehdä mitään
		if (self.doUpdateCheck==False and doUpgrade==False):
			return
	
		try:
			updateAvailable=False
			uurl="http://kapsi.fi/ighea/saunavisio/"
			data = urllib2.urlopen(uurl+"/latest").read()
			latest = data.split(" ")[0]
			filu = data.split(" ")[1]
			latest=float(latest)
			current=float(self.versio)
			latestFileUrl=uurl+"/"+filu
		except Exception, value:
			print value
			if (doUpgrade):
				print "*** Tietoja uusimmasta versioista ei voitu ladata! ***\n"
				print "*** Yritä myöhemmin uudelleen! ***\n"
			return

		if (latest > current):
			if (doUpgrade==True):
				try:
					print "\n*** Uusi versio "+str(latest)+" saatavilla! ***"
					print "\n*** Nykyinen versio: "+ str(current)+""
					print ""
					if (silentUpgrade==True):
						vastaus="k"
					else:
						vastaus=raw_input( "*** Haluatko päivittää sovelluksen nyt? [K/E Kyllä/Ei]: ")
					if (vastaus != "K" and vastaus != "Kyllä" and vastaus != "k"):
						print "\n*** Päivittäminen keskeytettiin! ***\n"
					else:
						print "\n>>> Aloitetaan päivitys..."
						print "<<< Ladataan tiedosto '"+latestFileUrl+"'..."
						newdata=urllib2.urlopen(latestFileUrl).read()
						print ">>> Päivitetään tiedosto '"+sys.argv[0]+"'..."
						nfile = open(sys.argv[0],"w")
						nfile.write(newdata)
						nfile.flush()
						nfile.close()
						print "\n*** Päivitys suoritettu! ***"
						print ">>> Tietoa muutoksista ja sovelluksen käytöstä löydät osoitteesta:"
						print ">>> "+uurl+"LUEMINUT.txt\n"
						return
				except IOError:
					print "*** Päivitys epäonnistui! ****"
					print "*** Tarkista, että sinulla on kirjoitusoikeudet tiedostoon:"
					print ">>> "+sys.argv[0]+""
				return
			else:
				updateAvailable=True
				print "\n*** Uusi versio "+str(latest)+" on saatavilla! ***\n"	
				print ">>> Tietoa muutoksista ja sovelluksen käytöstä löydät osoitteesta:"
				print ">>> "+uurl+"LUEMINUT.txt"
				print "\n>>> Voit ladata päivityksen käsin osoitteesta:"
				print ">>> "+latestFileUrl+""
				print ">>> tai automaattisesti suorittamalla komennon: "
				print ">>> '"+sys.argv[0]+" päivitä'"
		elif (doUpgrade==True):
			print "\n*** Päivitystä ei ole saatavilla! ***\n"
		return


	# Pätäkää NettiVision kahtelluu varatten, käyttellöö ihan sit perus videoplayer-jutsuu
	def showTV(self, schannel=""):
		
		# Kun eka osa mätsää tarpeeks kanavan kaa nii pannaa telekkuu pyörimmää, muuten listattaa kaik kanavvat
		if (len(schannel) > 0):
			for channel in self.channels:
				chan = channel[0]
				url = channel[1]
				if (chan.find(schannel) != -1):
					print "\n>>> Aloitetaan kanavan '"+chan+"' toisto:"
					print self.videoplayer
					if (isWindowsOS()):
                                                class WRUN(threading.Thread):
                                                        def __init__(self, cmd):
                                                                threading.Thread.__init__(self)
                                                                self.cmd = cmd
                                                                return
                                                        def run(self):
                                                                os.system(self.cmd)
                                                                return
                                                                
						thread = WRUN('\"'+self.videoplayer+ '\" ' + url)
                                                thread.start()
					else:
						os.system(self.videoplayer+' "'+url+'" &')

					return
		else:
			print "*** Yksikään kanava ei vastannut annettua kanavaa '"+schannel+"'! ***\n"
			print ">>> Mahdolliset kanavat:"
			for channel in self.channels:
				print "\t"+channel[0]
		return		


	# Asetusten lataaminen
	def loadSettings(self):
		try:
			# Ladataan asetustiedosto levyltä
			self.Config.load()
		
			# Asetetaan luetut arvot paikoilleen
			self.username = self.Config.get("username")
			self.password = self.Config.get("password")
			self.searchwords = self.Config.get("searchwords")
			self.videoplayer = self.Config.get("videoplayer")
			self.doUpdateCheck = self.Config.get("doupdatecheck")
			self.downloaddirectory = self.Config.get("downloaddirectory")
			self.downloadUseSubDirs = self.Config.get("downloadUseSubDirs")

		except IOError:
			print "\n*** Asetustiedoston '"+self.configfile+"' lukemisessa tapahtui virhe!"
			print "*** Tarkista, että tiedostoon on ainakin lukuoikeudet!\n"
			return False
	
		return True
		

	# Asetusten tallentaminen	
	def saveSettings(self):
		
		self.Config.set("username", self.username)
		self.Config.set("password", self.password)
		self.Config.set("searchwords", self.searchwords)
		self.Config.set("videoplayer", self.videoplayer)
		if (self.downloaddirectory.strip()[-1] != os.path.sep):
				self.downloaddirectory = self.downloaddirectory + os.path.sep
		self.Config.set("downloaddirectory", self.downloaddirectory)
		self.Config.set("downloadUseSubDirs", self.downloadUseSubDirs)
		self.Config.set("doupdatecheck", self.doUpdateCheck)

		# Ja kirjoitetaan levylle
		self.Config.save()

		return


	# Poistaa hakusanan, palauttaa True jos onnistuu, muutoin False
	def delSearchWord(self, line):
		try:
			self.searchwords.remove(line)
			self.saveSettings()
			return True
		except ValueError:
			print "*** Poistettavaa termiä '"+line+"' ei löytynyt!\n"
			return True
		return False

	def addSearchWord(self, line):
		try:
			self.searchwords.append(line)
			self.saveSettings()
			return True
		except ValueError, value:
			print "*** Asetettaessa hakusanaa '"+line+"' tapahtui virhe:", value
		return False

			
	def checkUsernameAndPassword(self, forceCreateConfig=False):
		if (self.username=="" or self.password==""):
			print "\n*** SaunaVisio aputyökalun käyttöönotto: \n"
			print "*** Ennen kuin jatkat tutustu tiedostoon:"
			print "*** http://kapsi.fi/ighea/saunavisio/LUEMINUT.txt\n"
		
			print ">>> Käyttäjätunnus (username) ja/tai salasana (password) on asettamatta! <<<"
			
			print "*** Luultavasti asetustiedostoa '"+self.configfile+"' ei ole olemassa.\n"

			if (forceCreateConfig):
				vastaus = "k"
			else:	
				vastaus=raw_input( "*** Haluatko luoda asetustiedostopohjan nyt? [K/E Kyllä/Ei]: ")

			if (vastaus != "K" and vastaus != "Kyllä" and vastaus != "k"):
				print "\n*** Asetustiedostoa ei luotu!\n"
			else:
				try:
					self.Config.save()
					print "\n*** Asetustiedostopohja luotu onnistuneesti! ("+self.configfile+") ***"
					print "*** Aloita sovelluksen käyttö muokkaamalla asetustiedosto mieleiseksesi! ***\n"
				except IOError:
					print "\n<<< Tiedostoon '"+self.configfile+"' ei voitu kirjoittaa! >>>\n"
			
		return


	# Palauttaa None jos kaikki sivukirjautumisyritykset menevät metsään
	def openURL(self, url, userAgent="Mozilla/5.0 (X11; U; Linux i686; fi-FI; rv:1.9) Gecko/2008052912 Firefox/3.0"):
		data=""
		failmsgList = ["Kirjautuminen epäonnistui. Tarkista tunnus ja/tai salasana.",'<form method="post" action="/tvrecorder/index.sl" name="svlogin">']
		
		
		# Kirjaudutaan 15 minuutin välein uudelleen palveluun ja uusitaan keksit, jos vaikka vältyttäisiin
		# "ei tietoa"-bugilta...
		if ( (self.lastLoginTime + (60*15)) < time.time() ):
			self.isLoginSuccess=False
			self.lastLoginTime=time.time()
			self.cookieJar = cookielib.CookieJar()
			print "<> Pakotetaan uudelleenkirjautuminen. <>"

		# Kunnes tulee kehiteltyä järkevämpi systeemi, pidetään lippu korkealla:
		self.reloginRetrys = 3
		
		
		# Vainoharhaisuus-moodi, odotellaan satunnaisaika sivukutsujen välissä
		if (self.paranoiaMode==True):
			self.doIdle()

		# Suoritetaan kirjautuminen, jos ei vielä olla niin tehty
		while (self.isLoginSuccess==False and self.reloginRetrys > 0):
			loginTryFailed = False
			# Luodaan kirjautumiselle pyyntö		
			print "Kirjaudutaan palveluun..."
			#print self.username, self.password
			request = urllib2.Request("http://www.saunavisio.fi/tvrecorder/index.sl?username="+self.username+"&password="+self.password)
			request.add_header('User-Agent', userAgent)  
			opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookieJar))
			# Tehdään sivupyyntö
			try:
				cFile = opener.open(request)
				data = cFile.read()
				cFile.close()
			except urllib2.URLError,value:
				print "!!! Kirjauduttaessa SaunaVisio Web-palveluun tapahtui seuraava virhe: !!!"
				print value
				print "\n*** Yritä myöhemmin uudelleen tai tarkista käyttäjätunnus ja salasana! ***\n"
				
				#raise
				#return
				
			# Tarkastetaan onnistuttiinko
			for failmsg in failmsgList:
				if (data.find(failmsg) == -1 and data != ""):
				# Vikaviestiä failmsg ei löydy palvelimen palauttamasta datasta. Kirjautuminen onnistui(?), jatketaan
					self.isLoginSuccess=True
					#print data
				else:
					self.isLoginSuccess=False
					# Reisille meni, yritetään reloginRetryn puitteissa uudelleen
					print "!!! Kirjautuminen epäonnistui, yritetään uudelleen 2 sekunnin kuluttua !!!"
					self.doIdle(2,2)
					self.reloginRetrys = self.reloginRetrys - 1
					break
			# Iloitaan kirjautumisen onnistumisesta vasta tässä:
			if (self.isLoginSuccess):
				print "*** Kirjautuminen onnistui! ***"
	
		if (self.reloginRetrys <= 0 and self.isLoginSuccess==False):
			print "\n!** Kaikki kirjautumisyritykset epäonnistuivat. Tarkista tunnuksesi! **!\n"
			raise Exception("Kaikki kirjautumisyritykset epäonnistuivat. Tarkista tunnuksesi!")
			return data

		# Suoritetaan varsinainen sivupyyntö

		try:
			request = urllib2.Request(url)
			request.add_header('User-Agent', userAgent)  
			opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookieJar))

			# Tehdään sivupyyntö
			cFile = opener.open(request)
			data = cFile.read()
			cFile.close()
		except Exception, value:
			print "Poikkeus: ", value
			print "Data:\n", data

		if (data==""):
			print "Ei dataa? Nyt meni jokin metsään ja pahasti..."
			print "CookieJar:", self.cookieJar
		
		return data


	def getValue(self, merkkijono, muuttuja,erotina='="',erotinb='"'):
		'''Parsii merkkijono:sta muuttuja:n, erottimien välistä. Palauttaa merkkijonon tai "NotFound" '''
		spos = merkkijono.find(muuttuja)
		if (spos == -1):
			return "NotFound"
		spos = spos+len(muuttuja)+len(erotina)
	
		epos = merkkijono.find(erotinb,spos)
		tulos=merkkijono[spos:epos]
		return tulos


	def setToBeRecord(self, programid):
		'''Asettaa yksittäisen ohjelman programid:n perusteella tallennettavaksi'''
		try:
			data = self.openURL("http://www.saunavisio.fi/tvrecorder/program.sl?record="+programid, self.cookieJar)
			return True
		except Exception, value:
			print value
			return False


	def printSearchList(self):
		'''Tulostaa hakusanalistan'''
		items=""
		for item in self.searchwords:
			if (self.searchwords[len(self.searchwords)-1]==item):
				items = items + item
			else:	
				items = items + item+", "
		print "*** Ohjelmien hakusanalista: "+items+"\n"



	def filePathAndNameCreator(self, name, date, runtime, extension="ts"):
		destFileName = name+' - '+date+' ('+runtime+').'+extension

		if (self.downloadUseSubDirs):
			doubledot = name.find(":")
			if (doubledot != -1):
				# Leikkaa ja liimaa ;)
				subdir = name[:doubledot] + os.path.sep
			else:
				subdir = name + os.path.sep
			destFilePath = self.downloaddirectory + subdir
		else:
			subdir = ""
			destFilePath = self.downloaddirectory + subdir
			
		
		# Windöös korajuksii		
		if (isWindowsOS()):
			# Tiedostojärjestelmä rajoituksia, duh!
			dFPa = destFilePath[:3]
			dFPb = destFilePath[3:].replace(':','_').replace('?','')
			destFilePath = dFPa + dFPb
			destFileName=destFileName.replace(':','_')
			destFileName=destFileName.replace('?','')
		
			# UTF-8 -> kohdemerkistö
			destFileName = destFileName.encode(sys.getfilesystemencoding(), "ignore")
			destFilePath = destFilePath.encode(sys.getfilesystemencoding(), "ignore")

		return (destFilePath, destFileName)

	
	def fetchDownloadUrl(self, id, verbose=True):
		'''Noutaa id:n perusteella kasan ohjelman tietoja'''
		
		kuvaus=nimi=aika=kesto=""
		cL=0
		id = id.strip()

		data = self.openURL("http://www.saunavisio.fi/tvrecorder/program.sl?programid="+id+"&view=true", self.cookieJar)
		
#<td class="prgrinfo1a">

#<b>Kanava</b>: Nelonen<br/>
#<b>Ohjelma</b>: South Park (K15)<br/>        
#<b>Aika</b>: 04.08.2008 23:25<br/>
#<b>Kesto</b>: 30 min<br/>
#<p>Vesirokko. Kenny sairastuu vesirokkoon ja äidit haluavat toistenkin poikien sairastavan sen, jotta se ei kiusaisi heitä myöhemmin. Kun pojat pääsevät äitien juonesta perille, he päättävät kostaa vanhemmilleen.</p>
#</td>
		

		progInfoParserStarted=False
		for line in data.splitlines():
		
			if (line.find('<td class="prgrinfo1a">') != -1):
				cL=0
				progInfoParserStarted=True

			if (progInfoParserStarted==True and line.find('</td>') != -1):
				progInfoParserStarted=False
				
			if (progInfoParserStarted==True):
				cL+=1
				if (cL==2):
					kanava = self.getValue(line, "<b>Kanava</b>",":","<br").strip()
				if (cL==3):
					nimi = self.getValue(line, "<b>Ohjelma</b>",":","<br").strip()
				if (cL==4):
					aika = self.getValue(line, "<b>Aika</b>",":","<br").strip()
				if (cL==5):
					kesto = self.getValue(line, "<b>Kesto</b>",":","<br").strip()
				if (cL==6):
					kuvaus = line.replace('<p>','').replace("</p>",'')
				#print line


		durl=self.getValue(data,"doGo('","","');")
		
		if (data == "" or nimi==""):
			print "\n*** Tallennetta ohjelmatunnuksella "+id+" ei löytynyt! ****\n\n"
			if (data==""):
				print "Tietomäärä on nolla!"
			if (nimi=="NotFound"):
				print "NotFound"
			print self.cookieJar
			raise Exception("Tallennetta ohjelmatunnuksella "+id+" ei löytynyt!")
			return False
		
		# Kootaan kohdetiedoston nimi, jos alihakemistot on käytössä.. pilkotaan ohjelman nimi kaksoispisteestä alihakemistoksi
		
		destFilePath, destFileName = self.filePathAndNameCreator(name=nimi, date=aika, runtime=kesto)
		'''
		destFileName = nimi+' - '+aika+' ('+kesto+').ts'
		if (self.downloadUseSubDirs):
			doubledot = nimi.find(":")
			if (doubledot != -1):
				# Leikkaa ja liimaa ;)
				subdir = nimi[:doubledot] + os.path.sep
			else:
				subdir = nimi + os.path.sep
			destFilePath = self.downloaddirectory + subdir
		else:
			subdir = ""
			destFilePath = self.downloaddirectory + subdir
			
		
		# Windöös korajuksii		
		if (isWindowsOS()):
			# Tiedostojärjestelmä rajoituksia, duh!
			dFPa = destFilePath[:3]
			dFPb = destFilePath[3:].replace(':','_').replace('?','')
			destFilePath = dFPa + dFPb
			destFileName=destFileName.replace(':','_')
			destFileName=destFileName.replace('?','')
		
			# UTF-8 -> kohdemerkistö
			destFileName = destFileName.encode(sys.getfilesystemencoding(), "ignore")
			destFilePath = destFilePath.encode(sys.getfilesystemencoding(), "ignore")
		'''
		finalFileName =  destFilePath + destFileName

		#print finalFileName
		
		
		wgetcmd = 'wget -c "' + durl + '" -O "' + finalFileName + '"'

		if (verbose):
			print ">>> Ohjelma: "+nimi+" - "+kesto+" - "+aika+"\n"

			print kuvaus+"\n"

			print ">>> Latausosoite:\n"
			print durl+"\n"

			print ">>> Suora komenta wget-ohjelmalle tallenteen lataamiseksi:\n"
			print wgetcmd+"\n"

		return (durl, id, nimi, aika, kesto, wgetcmd, kuvaus, destFilePath, destFileName)


	def playRecord(self, id):
		print "Aloitetaan toisto ohjelmatunnuksella "+id+" käyttäen videosoitinta: "+self.videoplayer
		url, id, programn, programdate,programtime, wgetcmd, pinfo, destFilePath, destFileName = self.fetchDownloadUrl(id, False)
		print self.videoplayer
	        exitcode = 0
	        print url
		if (isWindowsOS()):
	        	cmd = '\"\"'+self.videoplayer+ '\" \"'+url+'\"\"'
	        	print "Komento :", cmd
	                exitcode=os.system(cmd)
		else:
	                exitcode=os.system(self.videoplayer+' "'+url+'"')
		if (exitcode != 0):
			#print "Exitcode: ",exitcode
			raise Exception("Suoritettaessa komentoa '"+self.videoplayer+"' tapahtui virhe!", exitcode)
		
		return exitcode

	def playVideo(self, videofile):
		'''Toistaa videon videofile asetetulla videosoittimella'''
		print "Aloitetaan videon "+videofile+" toisto käyttäen videosoitinta: "+self.videoplayer
		print self.videoplayer
	        class PlayVideoThread(threading.Thread):
	        	def __init__(self, parent):
	        		threading.Thread.__init__(self)
	        		self.parent = parent
	        		return
	        	def run(self):
	        		exitcode = 0
				if (isWindowsOS()):
	        			cmd = '\"\"'+self.parent.videoplayer+ '\" \"'+videofile+'\"\"'
	        			print "Komento :", cmd
	                		exitcode=os.system(cmd)
				else:
	                		exitcode=os.system(self.parent.videoplayer+' "'+videofile+'"')
				if (exitcode != 0):
					#print "Exitcode: ",exitcode
					raise Exception("Suoritettaessa komentoa '"+self.parent.videoplayer+"' tapahtui virhe!", exitcode)
	        	
	        		return
		thread = PlayVideoThread(self)
		thread.start()
		return


	def beginDownload(self, ID):
		durl, id, programn, programdate,programtime, wgetcmd, pinfo, destFilePath, destFileName = self.fetchDownloadUrl(ID, False)
		print "Aloitetaan tallenteen '"+programn+"' ("+programdate+") lataus:"
		if (not os.path.exists(destFilePath)):
			print "Hakemisto "+destFilePath+" ei ole olemassa, luodaan!"
			os.mkdir(destFilePath)
		
		result = os.system(wgetcmd+"" )
		print "Valmis. ",result
		return result
		

	def doIdle(self, mintime=1,maxtime=60,notice=False):
		rtime=random.randint(mintime,maxtime)
		if (notice):
			print "*** Odotellaan "+str(rtime)+" sekuntia... ***"
		time.sleep(rtime)
		return
	
	
	def cancelRecordingRequest(self, IDList, showProgramInfo=False):
		if (not type(IDList) == list):
			IDList = [IDList]
		
		showProgramInfo=True
		if (len(IDList)>1):
			print "*** Peruttavien ohjelmien ohjelmatunnuksia enemmän kuin yksi, lisätietoja ei näytetä!"
		for ID in IDList:
			print "\n*** Perutaan tallennuspyyntö ohjelmatunnukselle: "+ID
			durl, ID, programn, programdate, programtime, wgetcmd, pinfo, destFilePath, destFileName = self.fetchDownloadUrl(ID, False)
		
			if (showProgramInfo):
				print ">>> Ohjelma: "+programn
				print ">>> Kesto: "+programtime
				print ">>> Ajankohta: "+programdate
				print "\n>>> Kuvaus:\n"+pinfo+"\n"
	
			# Nyppäistään sivulta ohjelmasta lisädataa
			data = self.openURL("http://www.saunavisio.fi/tvrecorder/program.sl?programid="+ID, self.cookieJar)
			#print data
			if (data.find('<a href="program.sl?programid='+ID+'&remover=') != -1):
				# Suoritetaan varsinainen tallennuspyynnön peruminen:	
				#<a href="program.sl?programid=212694&remover=592564">
				rmID=self.getValue(data,"&remover","=",'">')
				self.openURL("http://www.saunavisio.fi/tvrecorder/program.sl?programid="+ID+'&remover='+rmID, self.cookieJar)				
				print "\n*** Tallennuspyyntö peruttu! ***\n"
				return True
			elif (data.find('<a href="program.sl?programid='+ID+'&removep=') != -1):
				print "\n*** Kohteen tallennus on jo suoritettu, pyyntöä ei voida perua! ***\n"
			else:
				print "\n*** Kohdetta ei ole merkitty tallennettavaksi! ***\n"
	
		print "*** Valmis! ***\n"
		return False
	
	
	def setRecordings(self, recordIDList=[]):
		# Asetetaan yksittäinen ohjelma tallennettavaksi, käskytetty "tallenna [ID]"
		for pID in recordIDList:
			print "\n*** Asetetaan yksittäinen ohjelma tallennettavaksi:"
			print "<<< Haetaan tietoja ohjelmatunnukselle: "+pID
			durl, ID, programn, programdate, programtime, wgetcmd, pinfo, destFilePath, destFileName =  self.fetchDownloadUrl(pID,verbose=False)
		
			print ">>> Ohjelma: "+programn
			print ">>> Kesto: "+programtime
			print ">>> Ajankohta: "+programdate
			print "\n>>> Kuvaus:\n"+pinfo+"\n"
			# Suoritetaan varsinainen asettaminen:
			self.setToBeRecord(ID)
			print "\n*** Tallennus asetettu! ***\n"
		print "**** Valmis! ***\n"
		return
	
	
	def destroyRecording(self, ID):
		rID=""
		try:
			data = self.openURL("http://www.saunavisio.fi/tvrecorder/program.sl?programid="+ID)
			lines = data.splitlines()
			for line in lines:
				if (line.find('<a href="program.sl?removep=') != -1):
					print "roo!"
					print line
					rID = self.getValue(line, '<a href="program.sl?removep','=','">')
					break
			print "rID:"+rID
			print "Tuhotaan tallenne: "+ID
			self.openURL("http://www.saunavisio.fi/tvrecorder/program.sl?removep="+rID)
			return True
		except Exception, value:
			print value
			return False
		return False
	
	
	def printUsage(self):
		print "Käyttö:"
		print " hakusanat          - Tulostaa nykyiset hakusanat ruudulle"
		print " lisää [sana]       - Lisää hakusanan listaan"
		print " poista [sana]      - Poistaa hakusanan listalta, jos olemassa"
		print " listaa             - Näyttää nykyisiä hakusanoja vastaavat ohjelmat. Voi"
		print "                      hyödyntää samoja vipuja, kuin haussa"
		print " uudet [kuvaus]     - Listaa tuoreimmat valmistuneet tallennukset, [kuvauksella]"
		print " tallenna [IDt]     - Asettaa ohjelmat tunnuksilla [IDt] tallennettavaksi"
		print " tallenna           - Asettaa tallennukset hakusanojen perusteella"
		print " crontallenna       - Sama kuin yllä, mutta odottaa sivupyyntöjen välillä 1-60s."
		print " peruuta [IDt]      - Peruu tallenteille [IDt] asetetun tallennuspyynnöt"
		print " hae [vipu] [haku1] - Etsi ohjelmia ja tallenteita. [vipu] voi olla joko --uusi,"
		print "                      --tallennettu tai --pyyntö eli --u, --t tai --p."
		print " päivitä            - Pyrkii päivittämään sovelluksen uusimpaan versioon"
		print " tiedot [ID]        - Palauttaa ohjelman tiedot ja osoitteen videon lataamiseksi"
		print " lataa [ID]         - Aloittaa tallenteen lataamisen sovelluksella wget"
		print " toista [ID]        - Aloita tallenteen katselu"
		print " tv [Kanava]        - Aloita videosoittimella TV-kanavan katselun NettiVisiosta"              
		print " videosoitin [prog] - Aseta käytettävä videosoitin," 
		print "                      nykyinen: '"+self.videoplayer+"'"
	
		print "\n  "+SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED+" = Valmis tallennus, "+SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST+" = Merkattu tallennettavaksi,\n  "+SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW+" = uusi ohjelma"
		print ""
		# Tulostetaan hakusanalista
		self.printSearchList()
		# ja tarkistetaan onko uutta versiota saatavissa
		self.checkForUpdate()
		# Lopuksi lopetetaan sovelluksen suoritus.
		return
		# Done
	
	
	def showLatestRecordings(self, showInfo=False, verbose=True):
		# Haetaan tiedot uusimmista tallenteista
		data = self.openURL("http://www.saunavisio.fi/tvrecorder/ready.sl")
	
		# Parsitaan hakutuloksesta ohjelmatiedot ja tallennetaan ne taulukkoon ohjelmalista
		programParserStarted=False
		hakutaulu = data.splitlines()
		aika=kanava=ID=nimi=kuvaus=""
		ohjelmalista=[]
		cL=0
		for line in hakutaulu:
			#1 ajankohta
			#2 kesto
			#? kanava
			#4 ohjelma ? Ruma tyhmä tyhjä rivi, prkl :E
			if (programParserStarted==True):
				cL = cL + 1
				if (cL==1):
					# Ajankohta
					aika=self.getValue(line,"<t","d>","</td>")
				if (cL==2):
					#kanava=getValue(line,"<t","d>","</td>").strip()
					# Kesto
					aika = aika + " / "+ self.getValue(line,"<t","d>","</td>").strip()
				if (cL==3):
					# Kanava
					kanava=self.getValue(line,"<t","d>","</td>").strip()
				if (cL==4):
					# ID
					ID=self.getValue(line,'">','<a href="program.sl?programid=','"')
					# Kuvaus
					kuvaus=self.getValue(line, 'title','="','">')
					print len(kuvaus)
					# Nimi
					#nimi = self.getValue(line, kuvaus+'"','>','</a></td>')
					nimi = self.getValue(line, '"','>','</a></td>')
					sep = nimi.rfind('">')
					nimi = nimi[sep+2:]
										
			# Sopivan lohkon alun löydyttyä aloitetaan parsiminen				
			if ( line.startswith('<tr class="') ):
				#if (getValue(line,"class") == "odd" or getValue(line,"class") == "even" ):
				if (self.getValue(line,"class").startswith("odd") or self.getValue(line,"class").startswith("even") ):
					programParserStarted=True
					cL=0
			# Ohjelmalohko päättyy, lopetetaan parsiminen
			if ( line == "</tr>" and programParserStarted==True ):
				programParserStarted=False
				# Lisätään, tuorein ensin:
				if (nimi != "NotFound" and ID != "NotFound"):
					# Kaikki uusissa tallenteissa olevat ohjelmat oletetaan tallennetuiksi:
					ohjelmalista.insert(0,[ID,kanava,aika,nimi,kuvaus, SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED])
		# Ohjelmatietojen parsiminen päättyy
	
		# Tulostus:
		if (verbose):
			print "ID\tKanava\t\t Ajankohta\t\t\tNimi"
			for ohjelma in ohjelmalista:
				ID,kanava,aika,nimi,kuvaus,tila=ohjelma
				print ID +"  "+ kanava +"\t"+ aika +"  \t"+ nimi +" "
				if (showInfo):
					print "Kuvaus: "+kuvaus+""
			print "\n"
	
		return ohjelmalista


	def getFutureProgramsForNext24hours(self, verbose=False):
		'''Noutaa tiedot SaunaVision web-käyttöliittymän pääsivulta'''
		print "Noudetaan ohjelmatietoja...\n"
		# Haetaan tiedot ohjelmille tulevilta 24h
		data = self.openURL("http://www.saunavisio.fi/tvrecorder/index.sl")
	
		programParserStarted=False
		hakutaulu = data.splitlines()
		aika=tila=kanava=ID=nimi=kuvaus=""
		ohjelmalista=[]
		channelList = []
		currenthour=""
		cL=0
		cC=0
		
		currentDate=""
		nextDate=""
		dateParserStarted=False
		dateList = []
		timeLine=""
		
		for line in hakutaulu:
		
		
#<select name="showdate" onchange="this.form.submit()">
#<option value="su 03.08.2008" selected>Su 03.08.2008
#<option value="ma 04.08.2008" >Ma 04.08.2008
#<option value="ti 05.08.2008" >Ti 05.08.2008
#<option value="ke 06.08.2008" >Ke 06.08.2008
#<option value="to 07.08.2008" >To 07.08.2008
#<option value="pe 08.08.2008" >Pe 08.08.2008
#<option value="la 09.08.2008" >La 09.08.2008
#<option value="su 10.08.2008" >Su 10.08.2008
#</select>
			# Parsitaan nykyinen ja seuraava päivämäärä käytettäväksi aikaa
			if (line.startswith('<select name="showdate" onchange="this.form.submit()">')):
				dateParserStarted=True
			
			if (dateParserStarted and line.startswith('<option value="')):
				dateList.append(self.getValue(line, "value")[3:])
			
			if (dateParserStarted and line.startswith('</select>')):
				dateParserStarted=False
				currentDate=dateList[0]
				nextDate=dateList[1]
			
			if (line.startswith('<td class="time">') and line.endswith('</td>')):
				timeLine = self.getValue(line, '<td class="time', '">', '</td>')
				if (timeLine == "00:00"):
					currentDate=nextDate
		
			# Sijoitetaan ohjelmatietoihin oikea kanava
			if (len(channelList) > 0 and line == "<td>"):
				if (cC < len(channelList)):
					kanava = channelList[cC]
				cC+=1
			if (line.startswith('<td class="time">')):
				currenthour = self.getValue(line, '<td class="time"', '>', '</td>')
				cC=0
		
			# Parsitaan ohjelmatietoja
			if (line.startswith('<th class="channeltitle">')):
				channelList.append( self.getValue(line,'<th class="channeltitle', '">', '</th'))
			
			if ( line.startswith('<a name=') and line.find('href="program.sl?programid=') != -1):
				cL=0
				programParserStarted=True
				timename = self.getValue(line, ')"', ">", "</a>")
				
				ID = self.getValue(line, "program.sl?programid",'=', '" onmouseover="')
				
				aika = currentDate+" " + timename[:5].strip()
				nimi = timename[6:].strip()
				
				luokka = self.getValue(line, "class")
				if (luokka == "notrecorded"):
					tila=SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW
				elif ( luokka.startswith("recorded") ):
					tila=SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST
			
			if (programParserStarted):
				cL+=1
				if (cL == 11):
					kuvaus = line

			# Parsinta yhden ohjelman osalta valmis, lisätään listaan
			if (programParserStarted and line.startswith("</div>")):
					programParserStarted=False
					kuvaus = kuvaus.replace("&amp;", "&")
					nimi = nimi.replace("&amp;", "&")
					
					ohjelmalista.append([ID, kanava, aika, nimi, kuvaus, tila])

		# Tulostus:
		if (verbose):
			print "ID\tKanava\t\t Ajankohta\t\t\tNimi"
			for ohjelma in ohjelmalista:
				ID,kanava,aika,nimi,kuvaus,tila=ohjelma
				print ID +"  "+ kanava +"\t"+tila+"\t"+ aika +"  \t"+ nimi +" "
				print "Kuvaus: "+kuvaus+""
			
		#print channelList
		return ohjelmalista


	

	# Suorittaa haut saunavision nettikäyttöliittymässä searchwords-hakusanojen mukaan
	# ja palauttaa tulokset taulukkona []
	def getSearchData(self, searchwords, fetchProgramInfo=False):
		ohjelmalista=[]
		cL=0
		for hakusana in searchwords:
			hakusana=hakusana.strip()

			# Erikoisfiltteröintien parsinta:
	
			# Merkkien []-väliin voi määritellä alkavan tunnin jolta nauhoituksia merkataan tai välin alkavina tunteina [alku-loppu]
			hastime=False
			starthour=-1
			endhour=-1
		
			timestart = hakusana.find("[")
			timeend = hakusana.find("]")
			if (timestart != -1 and timeend != -1):
				timetmp = hakusana[timestart:timeend+1]
				hakusana = hakusana.replace(timetmp,"")
				#print timetmp
				#print hakusana
				timetmp=timetmp[1:-1]
				#print timetmp
				if (timetmp.find("-") != -1):
					starthour, endhour = timetmp.split("-")
					starthour = int(starthour)
					endhour = int(endhour)
				else:
					starthour = int(timetmp)
				hastime=True
				#print "Tulos: ",starthour,endhour
						
			# ^-merkki hakusanan alussa, hakusana vastaa ohjelman nimen alkua
			startswith=False
			# ^-merkki hakusanan lopussa, hakusana vastaa ohjelman nimen loppua
			endswith=False
		
			# Kanava-filtteri, jos @-merkki löytyy niin asetetaan loppuosa muuttujaan cchannel ja poistetaan hakusanan lopusta teuhka veke
			cposi = hakusana.rfind('@')
			if (cposi != -1):
				cchannel=hakusana[cposi+1:]
				hakusana=hakusana[:cposi]
			else:
				cchannel=""
	
			if (hakusana.startswith('^')):
				startswith=True
				hakusana=hakusana[1:]
			else:
				startswith=False
	
			if (hakusana.endswith('^')):
				endswith=True
				hakusana=hakusana[:-1]
			else:
				endswith=False
		
			# Suorita hakusanalle haku:
			hakudata = self.openURL("http://www.saunavisio.fi/tvrecorder/search.sl?q="+hakusana.replace(',',''))
		
			# Parsitaan hakutuloksesta ohjelmatiedot ja tallennetaan ne taulukkoon ohjelmalista
			programParserStarted=False
			hakutaulu = hakudata.splitlines()
			aika=kanava=ID=nimi=tila=kuvaus=""
			for line in hakutaulu:
				#1 aika
				#2 kanava
				#3 ohjelma
				if (programParserStarted==True):
					cL = cL + 1
					if (cL==1):
						aika=self.getValue(line,"<t","d>","</td>").strip()
						pvm,kello = aika.split()
						# Tunti on parsittavan ohjelman alkamistunti
						tunti=int(kello.split(":")[0])
						#print tunti
					if (cL==2):
						kanava=self.getValue(line,"<t","d>","</td>").strip()
					if (cL==3):
						ID=self.getValue(line,'<td>','<a href="program.sl?programid=','"')
						# Haluttaessa haetaan myös ohjelman kuvaus:
						if (fetchProgramInfo==True):
							proginfodata = self.openURL("http://www.saunavisio.fi/tvrecorder/program.sl?programid="+ID)
							proginfodata=proginfodata.splitlines()
							progInfoParserStarted=False
							for infoline in proginfodata:
								if (progInfoParserStarted==True):
									kuvaus=kuvaus+infoline
								if (infoline.find('<td class="prgrinfo2a" rowspan="2">') != -1):
									#print "Start!"
									kuvaus=""
									progInfoParserStarted=True
								if (progInfoParserStarted==True and infoline.find('</td>') != -1):
									#print "Stop"
									progInfoParserStarted=False
									kuvaus=kuvaus.replace('</td>','')
									#print kuvaus+"\n\n"
									break
								
									
						nimi=self.getValue(line, '">','','</a>')
						if (line.find('class="') != -1):
							tila=self.getValue(line,"class")
							if tila=="notrecorded":
								tila=SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW #Tallentamaton
							elif tila=="recorded":
								tila=SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST #Merkattu tallennukseen
						else:
							tila=SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED #Tallennettu
					# Ohjelma on "Löytynyt tuleva tallenne": ei lisätä listaa, koska esiintyisi kahdesti
					if (cL==4):
						if ( line.find('<td><input type="checkbox" name="remover" value="') != -1):
							programParserStarted=False
											
				# Sopivan lohkon alun löydyttyä aloitetaan parsiminen				
				if ( line.startswith('<tr class="') ):
					#if (getValue(line,"class") == "odd" or getValue(line,"class") == "even" ):
					#if (getValue(line,"class").startswith("odd") or getValue(line,"class").endswith("even") ):
					if (self.getValue(line,"class").startswith("odd") or self.getValue(line,"class").startswith("even") ):
						programParserStarted=True
						cL=0
				# Ohjelmalohko päättyy, lopetetaan parsiminen
				if ( line == "</tr>" and programParserStarted==True ):
					programParserStarted=False
					#print "'"+nimi+"' '"+hakusana+"'"
					# Kanavaan vastaaminen käytössä hakusanalla, mutta nykyinen ohjelma ei vastaa hakusanaa, ei tehdä mitään	
					if (cchannel != "" and cchannel != kanava):
						True
					elif (hastime == True):
						if (tunti >= starthour):
							#print tunti, starthour, endhour
							if (endhour == -1):
								ohjelmalista.append([ID,kanava,aika,nimi,kuvaus,tila])
							elif (tunti <= endhour):
								ohjelmalista.append([ID,kanava,aika,nimi,kuvaus,tila])
					# ^-merkki sekä alussa että lopussa hakusanaa, hakusana on täsmälleen hakutulos:
					elif (hastime == False and startswith==True and endswith==True and nimi.upper().startswith(hakusana.upper	()) and nimi.upper().endswith(hakusana.upper()) ):
						ohjelmalista.append([ID,kanava,aika,nimi,kuvaus,tila])
					# Hakusana on alkanut merkillä '^', jos ohjelman nimen alku vastaa hakusanaa, lisätään ohjelmal	istaan
					elif (hastime == False and startswith==True and endswith==False and nimi.upper().startswith(hakusana.upper	())):
					#print "'"+nimi+"' + '"+hakusana+"'"
						ohjelmalista.append([ID,kanava,aika,nimi,kuvaus,tila])
					# Hakusana on loppunut merkillä '^', jos ohjelman nimen loppu vastaa hakusanaa, lisätään ohjelmalistaan
					elif (hastime == False and startswith==False and endswith==True and nimi.upper().endswith(hakusana.upper	())):
						#print "'"+nimi+"' + '"+hakusana+"'"
						ohjelmalista.append([ID,kanava,aika,nimi,kuvaus,tila])
					# Erikoisempia hakuehtoja ei ole käytössä, lisätään osuma ohjelmalistaan, KUNHAN hakusana löytyy hakutuloksen nimestä!
					elif (hastime == False and startswith==False and endswith==False and nimi.upper().find(hakusana.upper()) != -1):
						ohjelmalista.append([ID,kanava,aika,nimi,kuvaus,tila])
			# Ohjelmatietojen parsiminen päättyy
		return ohjelmalista
	

	# Listataan hakutulokset ja asetetaan halutessa tallennukset
	def printSearchResults(self, programList, searchShowNew=True, searchShowRecorded=True, searchShowRequested=True, dorecording=False, onSetRecordingBeVerbose=True):
		#global cookieJar
	
		ohjelmalista=programList
		print "ID\tKanava\t Ajankohta\t\tNimi"
		for ohjelma in ohjelmalista:
			ID,kanava,aika,nimi,kuvaus,tila=ohjelma
			# Ollaan asettamassa uusia tallennuksia:
			if (dorecording == True):
				if (tila==SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW):
					# Tulostellaan tiedot, jos niin halutaan:
					if (onSetRecordingBeVerbose==True):
						print ID +"  "+ kanava +"  "+ aika +" \t"+ nimi +"  - N=>R"
					# Asetetaan tallennettavaksi:
					self.setToBeRecord(ID)
			else:
				if (tila==SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_NEW and searchShowNew==True or tila==SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_RECORDED and searchShowRecorded==True or tila==SAUNAVISIO_PROGRAM_STATE_IDENTIFIER_REQUEST and searchShowRequested==True):
					print ID +"  "+ kanava +"  "+ aika +" \t"+ nimi +"  - "+ tila
		return

####################################################################


if __name__ == "__main__":
	try:
		SV = SaunaVisio()
	
		SV.loadSettings()
		SV.checkUsernameAndPassword()
	
		searchShowNew=searchShowRecorded=searchShowRequested=True
		dorecording=False
		searchwords=[]
	
		# Komentoriviparametrit ja niiden parsinta:
		if (len(sys.argv) > 1):
			#"tallenna" ilman lisäparametrejä
			if (sys.argv[1] == "tallenna" and len(sys.argv)==2):
				dorecording=True
			#"tallenna" usealla ID:llä
			elif (sys.argv[1] == "tallenna" and len(sys.argv)>2):
				# Asetetaan yksi tai useampi tallenne ID:n perusteella tallennettavaksi
				recordIDList=[]
				for i in range(2,len(sys.argv)):
					recordIDList.append(sys.argv[i])
				SV.setRecordings(recordIDList)
				sys.exit()
			elif sys.argv[1] == "tulevat":
				SV.getFutureProgramsForNext24hours()
				sys.exit()
			# "crontallenna" 
			elif sys.argv[1] == "crontallenna":
				dorecording=True
				paranoiaMode=True
			elif sys.argv[1] == "uudet":
				# Jos parametreja on enemmän kuin yksi, näytetään kuvaus myös
				if (len(sys.argv) > 2):
					SV.showLatestRecordings(True)
				else:
					SV.showLatestRecordings(False)
				SV.checkForUpdate()
				sys.exit()
			elif sys.argv[1] == "listaa":
				# ei lisäoptiota, huomatkaa sydän... ahahaha...
				if (len(sys.argv) <3):
					True
				else:
				# annettiin hakuehto
					for i in range(2,len(sys.argv)):
						if (sys.argv[i].startswith("--")):
							searchShowNew=searchShowRecorded=searchShowRequested=False
					for i in range(2,len(sys.argv)):
						hs=sys.argv[i]
						if (hs=="--uusi" or hs=="--u"):
							searchShowNew=True
						elif (hs=="--tallennettu" or hs=="--t"):
							searchShowRecorded=True
						elif (hs=="--pyyntö" or hs=="--pyynto" or hs=="--p"):
							searchShowRequested=True
		
			elif sys.argv[1] == "päivitä" or sys.argv[1] == "paivita":
				SV.checkForUpdate(doUpgrade=True)
				sys.exit()
			elif sys.argv[1] == "hakusanat":
				SV.printSearchList()
				sys.exit()
			elif sys.argv[1] == "tv":
				# NettiVision kahtelu pätkää:
				channel=""
				if (len(sys.argv) > 2):
					channel = sys.argv[2]
				SV.showTV(channel)
				sys.exit()
			elif (len(sys.argv) > 2):
				if (sys.argv[1] == "hae"):
					#htmp=""
					searchwords=[]
					for i in range(2,len(sys.argv)):
						if (sys.argv[i].startswith("--")):
							searchShowNew=searchShowRecorded=searchShowRequested=False
					for i in range(2,len(sys.argv)):
						hs=sys.argv[i]
						if (hs=="--uusi" or hs=="--u"):
							searchShowNew=True
						elif (hs=="--tallennettu" or hs=="--t"):
							searchShowRecorded=True
						elif (hs=="--pyyntö" or hs=="--pyynto" or hs=="--p"):
							searchShowRequested=True
						else:
							searchwords.append(hs)
				elif (sys.argv[1] == "lisää" or sys.argv[1] == "lisaa"):
					# Lisää hakusana
					print "<<< Lisätään hakusana: "+sys.argv[2]+"\n"
					SV.addSearchWord(sys.argv[2])
					#SV.searchwords.append(sys.argv[2])
					#SV.saveSettings()
					SV.printSearchList()
					sys.exit()
				elif (sys.argv[1] == "poista"):
					print ">>> Poistetaan hakusana: "+sys.argv[2]+"\n"
					SV.delSearchWord(sys.argv[2])
					SV.printSearchList()
					sys.exit()
				elif (sys.argv[1] == "tiedot"):
					SV.fetchDownloadUrl(sys.argv[2])
					sys.exit()
				elif (sys.argv[1] == "lataa"):
					SV.beginDownload(sys.argv[2])
					sys.exit()
				elif (sys.argv[1] == "toista"):
					SV.playRecord(sys.argv[2])
					sys.exit()
				elif (sys.argv[1] == "peruuta"):
					IDList=[]
					for i in range(2,len(sys.argv)):
						IDList.append(sys.argv[i])
					SV.cancelRecordingRequest(IDList)
					sys.exit()
				elif (sys.argv[1] == "videosoitin"):
					# Asetetaan videosoitin
					SV.videoplayer=sys.argv[2]
					SV.saveSettings()
					print "Uusi videosoitin asetettu: "+SV.videoplayer
					sys.exit()
				else:
					## Jos komentoriviparametrejä ei annettu, tulostetaan käyttöohje
					SV.printUsage()
					sys.exit()
			else:
				SV.printUsage()
				sys.exit()
		else:
			SV.printUsage()
			sys.exit()
	
		
		# Tulostetaan hakusanalistaus
		SV.printSearchList()
		
		##
		## Aletaan suorittamaan hakusanoilla hakuja ja merkataan uudet ohjelmat tallennettaviksi, jos näin on haluttu
		if (dorecording == True):
			print ">>> Asetetaan ohjelmia tallennettaviksi..."
		else:
			print ">>> Suoritetaan hakua..."
		
	
	
		# Suoritetaan haut hakusanoilla
		if (len(searchwords) == 0):
			ohjelmalista = SV.getSearchData(SV.searchwords)
		else:
			ohjelmalista = SV.getSearchData(searchwords)
		
		# Mitään ei löytynyt, ilmoitetaan asiasta ja päätetään sovelluksen suoritus
		if (len(ohjelmalista)==0):
			print "\n*** Haulla ei löytynyt osumia! ****\n"
			sys.exit()
		else:
			# Löydettiin tuloksia, toimitaan sen mukaisesti
			SV.printSearchResults(ohjelmalista, searchShowNew, searchShowRecorded, searchShowRequested, dorecording)
			# Tarkistetaan lopuksi onko uudempaa versiota saatavilla, jos ei olla asettamassa tallenteita
			if (dorecording == False):
				SV.checkForUpdate()
		
		print "\n"
	except Exception, value:
		print "Poikkeus: ",value
