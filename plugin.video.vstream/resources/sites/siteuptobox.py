# -*- coding: utf-8 -*-
# vStream https://github.com/Kodi-vStream/venom-xbmc-addons
import json
import re
import xbmc
import xbmcgui

try:  # Python 2
    import urllib2
    from urllib2 import URLError as UrlError

except ImportError:  # Python 3
    import urllib.request as urllib2
    from urllib.error import URLError as UrlError
    from urllib.parse import urlencode

from resources.lib.comaddon import progress, dialog, addon, isMatrix, siteManager
from resources.lib.config import GestionCookie
from resources.lib.gui.gui import cGui
from resources.lib.gui.hoster import cHosterGui
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.handler.premiumHandler import cPremiumHandler
from resources.lib.handler.requestHandler import cRequestHandler, MPencode
from resources.lib.parser import cParser
from resources.lib.util import Quote


SITE_IDENTIFIER = 'siteuptobox'
SITE_NAME = '[COLOR dodgerblue]Compte UpToBox[/COLOR]'
SITE_DESC = 'Fichiers sur compte UpToBox'
URL_MAIN = siteManager().getUrlMain(SITE_IDENTIFIER)
NB_FILES = 100
BURL = URL_MAIN + '?op=my_files'
API_URL = 'https://uptobox.com/api/user/files?token=none&orderBy=file_created&dir=desc'
URL_MOVIE = ('&path=//', 'showMedias')

UA = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:61.0) Gecko/20100101 Firefox/61.0'
headers = {'User-Agent': UA}


def load():
    oGui = cGui()
    sToken = cPremiumHandler('uptobox').getToken()

    if not sToken:
        oGui.addText(SITE_IDENTIFIER, '[COLOR red]' + 'Nécessite un Compte Uptobox Premium ou Gratuit' + '[/COLOR]')
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('siteUrl', '//')
        oGui.addDir(SITE_IDENTIFIER, 'opensetting', addon().VSlang(30023), 'none.png', oOutputParameterHandler)
        oGui.setEndOfDirectory()
        return

    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', URL_MOVIE[0])
    oGui.addDir(SITE_IDENTIFIER, 'showSearch', 'Recherche', 'search.png', oOutputParameterHandler)

    oOutputParameterHandler.addParameter('siteUrl', URL_MOVIE[0])
    oGui.addDir(SITE_IDENTIFIER, URL_MOVIE[1], 'Mes vidéos', 'films.png', oOutputParameterHandler)

    oOutputParameterHandler.addParameter('siteUrl', URL_MOVIE[0])
    oGui.addDir(SITE_IDENTIFIER, 'showFile', 'Mes Fichiers', 'genres.png', oOutputParameterHandler)

    oGui.setEndOfDirectory()


def opensetting():
    addon().openSettings()


def showSearch():
    oGui = cGui()
    sSearchText = oGui.showKeyBoard()
    if sSearchText != False:
        sUrlSearch = '&path=//&searchField=file_name&search=' + sSearchText
        showMedias(sUrlSearch)


def showFile(sSearch=''):

    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    # VSlog('input   ' + str(sUrl))
    oParser = cParser()

    sOffset = 0
    if oInputParameterHandler.exist('sOffset'):
        sOffset = int(oInputParameterHandler.getValue('sOffset'))

    sNext = 0
    if oInputParameterHandler.exist('sNext'):
        sNext = int(oInputParameterHandler.getValue('sNext'))

    sToken = ''
    if oInputParameterHandler.exist('sToken'):
        sToken = oInputParameterHandler.getValue('sToken')

    sFoldername = ''
    if oInputParameterHandler.exist('sFoldername'):
        sFoldername = oInputParameterHandler.getValue('sFoldername')
        sUrl = sUrl + Quote(sFoldername).replace('//', '%2F%2F')

    sPath = ''
    if oInputParameterHandler.exist('sPath'):
        sPath = oInputParameterHandler.getValue('sPath')
        sUrl = sUrl + Quote(sPath).replace('//', '%2F%2F')

    if 'offset=' not in sUrl:
        sUrl = '&offset=0' + sUrl
    if 'limit=' not in sUrl:
        sUrl = '&limit=%d' % NB_FILES  + sUrl

    oPremiumHandler = cPremiumHandler('uptobox')
    sToken = oPremiumHandler.getToken()

    oRequestHandler = cRequestHandler(API_URL.replace('none', sToken) + sUrl)
    sHtmlContent = oRequestHandler.request()
    content = json.loads(sHtmlContent)
    if ('success' in content and content['success'] == False) or content['statusCode'] != 0:
        dialog().VSinfo(content['data'])
        oGui.setEndOfDirectory()
        return
    
    content = content['data']
    if not content:
        oGui.setEndOfDirectory()
        return

    total = len(content)
    sPath = getpath(content)
    
    # les dossiers en premier
    if not sSearch and 'folders' in content:
        folders = sorted(content['folders'], key=lambda f: f['fld_name'].upper())
        sFoldername = ''
        oOutputParameterHandler = cOutputParameterHandler()
        for folder in folders:
            if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
                sTitle = folder['name']
                sFoldername = folder['fld_name']
            else:
                sTitle = folder['name'].encode('utf-8')
                sFoldername = folder['fld_name'].encode('utf-8')
            sUrl = '&path=' + Quote(sFoldername).replace('//', '%2F%2F')
    
            oOutputParameterHandler.addParameter('siteUrl', sUrl)
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oGui.addDir(SITE_IDENTIFIER, 'showFile', sTitle, 'genres.png', oOutputParameterHandler)

    # les fichiers
    for file in content['files']:
        if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
            sTitle = file['file_name']
        else:
            sTitle = file['file_name'].encode('utf-8')

        sHosterUrl = URL_MAIN + file['file_code']

        oHoster = cHosterGui().checkHoster(sHosterUrl)
        if oHoster != False:
            oHoster.setDisplayName(sTitle)
            oHoster.setFileName(sTitle)
            cHosterGui().showHoster(oGui, oHoster, sHosterUrl, '')
        sNext += 1

    # Next >>>
    if not sSearch:
        if content['currentFolder']['fileCount'] != int(sNext):
            oOutputParameterHandler = cOutputParameterHandler()

            sOffset = int(sOffset) + NB_FILES

            oOutputParameterHandler.addParameter('siteUrl', API_URL.replace('none', sToken).replace('offset=0', 'offset=' + str(sOffset)))
            oOutputParameterHandler.addParameter('sToken', sToken)
            oOutputParameterHandler.addParameter('sNext', sNext)
            oOutputParameterHandler.addParameter('sOffset', sOffset)
            oOutputParameterHandler.addParameter('sPath', sPath)
            oGui.addNext(SITE_IDENTIFIER, 'showFile', 'Suite', oOutputParameterHandler)

    oGui.setEndOfDirectory()


def showMedias(sSearch=''):

    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    
    if sSearch:
        sSiteUrl = sSearch
    else:
        sSiteUrl = oInputParameterHandler.getValue('siteUrl')
    
    oPremiumHandler = cPremiumHandler('uptobox')
    sToken = oPremiumHandler.getToken()

    # parcourir un dossier virtuel, séparateur ':'
    searchFolder = ''
    if sSiteUrl[-1:] == ':':
        idxFolder = sSiteUrl.rindex('/')
        searchFolder = sSiteUrl[idxFolder+1:-1]
        sSiteUrl = sSiteUrl[:idxFolder]

    offset = 0
    limit = NB_FILES
    if 'offset=' not in sSiteUrl:
        sSiteUrl = '&offset=0' + sSiteUrl
    else:
        offset = int(re.search('&offset=(\d+)', sSiteUrl)[1])

    if 'limit=' not in sSiteUrl:
        sSiteUrl = '&limit=%d' % NB_FILES + sSiteUrl
    else:
        limit = int(re.search('&limit=(\d+)', sSiteUrl)[1])

    # Page courante
    numPage = offset//limit

    oRequestHandler = cRequestHandler(API_URL.replace('none', sToken) + sSiteUrl)
    sHtmlContent = oRequestHandler.request()
    content = json.loads(sHtmlContent)
    
    if ('success' in content and content['success'] == False) or content['statusCode'] != 0:
        dialog().VSinfo(content['data'])
        oGui.setEndOfDirectory()
        return
    
    content = content['data']
    if not content:
        oGui.setEndOfDirectory()
        return

    isMovie = isTvShow = isSeason = False
    path = content['path'].upper()
    isMovie = 'FILM' in path or 'MOVIE' in path
    isTvShow = 'SERIE' in path or 'SÉRIE' in path or 'TVSHOW' in path
    isAnime = '//ANIMES' in path or 'JAPAN' in path

    # ajout des dossiers en premier, sur la première page seulement
    if not isTvShow and not isAnime and not sSearch and numPage == 0 and 'folders' in content:
        addFolders(oGui, content, searchFolder)

    nbFile = 0
    if isMovie:
        nbFile = showMovies(oGui, content)
    elif isTvShow or isAnime:
        sSeason = False
        if 'sSeason' in sSiteUrl:
            sSeason = sSiteUrl.split('sSeason=')[1]
        
        if len(content['files'])>1 :
            nbFile = showEpisodes(oGui, sMovieTitle, content, sSiteUrl, sSeason)
        else:
            nbFile = showSeries(oGui, content, searchFolder, numPage)
    else:
        for file in content['files']:
            if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
                sTitle = file['file_name']
            else:
                sTitle = file['file_name'].encode('utf-8')
                
            sHosterUrl = URL_MAIN + file['file_code']
            oHoster = cHosterGui().checkHoster(sHosterUrl)
            if oHoster != False:
                oHoster.setDisplayName(sTitle)
                oHoster.setFileName(sTitle)
                cHosterGui().showHoster(oGui, oHoster, sHosterUrl, '')

    # Lien Suivant >>
    if not sSearch and nbFile == NB_FILES:
        sPath = getpath(content)
        nextPage = numPage + 1
        offset = nextPage * NB_FILES
        siteUrl = '&offset=%d&limit=%d&path=%s' % (offset, limit, sPath) 

        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('siteUrl', siteUrl)
        oOutputParameterHandler.addParameter('sMovieTitle', sMovieTitle)
        oGui.addNext(SITE_IDENTIFIER, 'showMedias', 'Page %d' % (nextPage+1), oOutputParameterHandler)

    oGui.setEndOfDirectory()


def addFolders(oGui, content, searchFolder = None):

    # dossiers trier par ordre alpha
    folders = sorted(content['folders'], key=lambda f: f['fld_name'].upper())

    sFoldername = ''

    # Sous-dossiers virtuels identifiés par les deux-points
    subFolders = set()
    oOutputParameterHandler = cOutputParameterHandler()

    for folder in folders:
        if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
            sTitle = folder['name']
            sFoldername = folder['fld_name']
        else:
            sTitle = folder['name'].encode('utf-8')
            sFoldername = folder['fld_name'].encode('utf-8')

        if searchFolder and not sTitle.startswith(searchFolder):
            continue

        isSubFolder = False
        if sTitle.startswith('REP_') or sTitle.startswith('00_'):
            isSubFolder = True

        if isSubFolder and ':' in sTitle:
            subName, subFolder = sTitle.split(':')
            if folder['path'].endswith(subName):
                sTitle = subFolder.strip()
            else:
                if searchFolder:
                    if subName == searchFolder:
                        sTitle = subFolder
                else:
                    if subName in subFolders:
                        continue
                    subFolders.add(subName)
                    sTitle = subName
                    sFoldername = sFoldername.replace(subFolder, '')

        if sTitle.startswith('REP_'):
            sTitle=sTitle.replace('REP_', '')
        if sTitle.startswith('00_'):
            sTitle=sTitle.replace('00_', '')

        sUrl = '&path=' + Quote(sFoldername).replace('//', '%2F%2F')
        
        if 'FILM' in sTitle.upper() or 'MOVIE' in sTitle.upper():
            sThumb = 'films.png' 
        elif 'SERIE' in sTitle.upper() or 'SÉRIE' in sTitle.upper() or 'TVSHOW' in sTitle.upper():
            sThumb = 'series.png'
        else:
            sThumb = 'genres.png'
        

        oOutputParameterHandler.addParameter('siteUrl', sUrl)
        oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
        oGui.addDir(SITE_IDENTIFIER, 'showMedias', sTitle, sThumb, oOutputParameterHandler)


def showMovies(oGui, content):
    
    numFile = 0
    
    # ajout des fichiers
    oOutputParameterHandler = cOutputParameterHandler()
    for file in content['files']:
        numFile += 1
        if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
            sTitle = file['file_name']
        else:
            sTitle = file['file_name'].encode('utf-8')
            
        sHosterUrl = URL_MAIN + file['file_code']
        
        # seulement les formats vidéo (ou sans extensions)
        if sTitle[-4] == '.':
            if sTitle[-4:] not in '.mkv.avi.mp4.m4v.iso':
                continue
            # enlever l'extension
            sTitle = sTitle[:-4]

        sMovieTitle = sTitle
        
        # recherche des métadonnées
        pos = len(sMovieTitle)
        sPattern = ['[^\w]([0-9]{4})[^\w]']
        sYear, pos = getTag(sMovieTitle, sPattern, pos)
        
        sPattern = ['HDLIGHT', '\d{3,4}P', '4K', 'UHD', 'BDRIP', 'BRRIP', 'DVDRIP', 'DVDSCR', 'TVRIP', 'HDTV', 'BLURAY', '[^\w](R5)[^\w]', '[^\w](CAM)[^\w]', 'WEB-DL', 'WEBRIP', '[^\w](WEB)[^\w]']
        sRes, pos = getTag(sMovieTitle, sPattern, pos)
        if sRes:
            sRes = sRes.replace('2160P', '4K')
        
        sPattern = ['TM(\d+)TM']
        sTmdbId, pos = getTag(sMovieTitle, sPattern, pos)

        sPattern = ['VFI', 'VFF', 'VFQ', 'SUBFRENCH', 'TRUEFRENCH', 'FRENCH', 'VF', 'VOSTFR', '[^\w](VOST)[^\w]', '[^\w](VO)[^\w]', 'QC', '[^\w](MULTI)[^\w]']
        sLang, pos = getTag(sMovieTitle, sPattern, pos)

        sMovieTitle = sMovieTitle[:pos].replace('.', ' ').strip()
        
        sTitle = sMovieTitle
        if sRes:
            sMovieTitle += ' [%s]' % sRes
        if sLang:
            sMovieTitle += ' (%s)' % sLang
        
        oOutputParameterHandler.addParameter('siteUrl', sHosterUrl)
        oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
        oOutputParameterHandler.addParameter('sYear', sYear)
        oOutputParameterHandler.addParameter('sRes', sRes)
        oOutputParameterHandler.addParameter('sLang', sLang)
        oOutputParameterHandler.addParameter('sTmdbId', sTmdbId)
        
        oGui.addMovie(SITE_IDENTIFIER, 'showHosters', sMovieTitle, '', '', '', oOutputParameterHandler)
        
    return numFile


def showSeries(oGui, content, searchFolder, numPage):
    # dossiers trier par ordre alpha
    folders = sorted(content['folders'], key=lambda f: f['fld_name'].upper())

    sMovieTitle = content['currentFolder']['name']

    numSeries = 0
    nbSeries = 0
    offset = numPage * NB_FILES

    # Sous-dossiers virtuels identifiés par les deux-points
    subFolders = set()
    oOutputParameterHandler = cOutputParameterHandler()

    for folder in folders:
        
        numSeries += 1
        if numSeries <= offset:
            continue
        
        if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
            sTitle = folder['name']
            sFoldername = folder['fld_name']
        else:
            sTitle = folder['name'].encode('utf-8')
            sFoldername = folder['fld_name'].encode('utf-8')

        if searchFolder and not sTitle.startswith(searchFolder):
            continue

        # dossier
        isSubFolder = False
        if sTitle.startswith('REP_') or sTitle.startswith('00_'):
            isSubFolder = True

        if isSubFolder and ':' in sTitle:
            subName, subFolder = sTitle.split(':')
            if folder['path'].endswith(subName):
                sTitle = subFolder.strip()
            else:
                if searchFolder:
                    if subName == searchFolder:
                        sTitle = subFolder
                else:
                    if subName in subFolders:
                        continue
                    subFolders.add(subName)
                    sTitle = subName
                    sFoldername = sFoldername.replace(subFolder, '')

        if sTitle.startswith('REP_'):
            sTitle=sTitle.replace('REP_', '')
        if sTitle.startswith('00_'):
            sTitle=sTitle.replace('00_', '')

        sUrl = '&path=' + Quote(sFoldername).replace('//', '%2F%2F')
        # sMovieTitle = sTitle
        
        oOutputParameterHandler.addParameter('siteUrl', sUrl)
        oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
        
        if isSubFolder:   # dossier
            oGui.addDir(SITE_IDENTIFIER, 'showMedias', sTitle, 'genres.png', oOutputParameterHandler)
        else:           # série
            if 'SAISON' in sTitle.upper() or 'SEASON' in sTitle.upper() :
                saison = int(re.search('(\d+)', sTitle)[1])
                sUrl += '&sSeason=%d' % saison
                oOutputParameterHandler.addParameter('siteUrl', sUrl)
                oOutputParameterHandler.addParameter('sMovieTitle', sMovieTitle)

                oGui.addSeason(SITE_IDENTIFIER, 'showMedias', sMovieTitle + ' ' + sTitle, '', '', '', oOutputParameterHandler)
            elif sMovieTitle.upper() == 'ANIMES' or 'JAPAN' in sMovieTitle.upper():
                oGui.addAnime(SITE_IDENTIFIER, 'showMedias', sTitle, '', '', '', oOutputParameterHandler)
            else:
                oGui.addTV(SITE_IDENTIFIER, 'showMedias', sTitle, '', '', '', oOutputParameterHandler)

        nbSeries += 1
        if nbSeries == NB_FILES:
            break
            
    return nbSeries


def showEpisodes(oGui, sMovieTitle, content, sSiteUrl, sSeason):
    
    nbFile = 0
    

    if not sSeason:
        saisons = set()
        
        # Recherche des saisons
        for file in content['files']:
            nbFile += 1
            if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
                sTitle = file['file_name']
            else:
                sTitle = file['file_name'].encode('utf-8')
                
            # Recherche saisons et episodes
            sa = ''
            m = re.search('(|S|saison)(\s?|\.)(\d+)(\s?|\.)(E|Ep|x|\wpisode)(\s?|\.)(\d+)', sTitle, re.UNICODE | re.IGNORECASE)
            if m:
                sa = m.group(3)
            else:  # Juste l'épisode
                m = re.search('(^|\s|\.)(E|Ep|\wpisode)(\s?|\.)(\d+)', sTitle, re.UNICODE | re.IGNORECASE)
                if m:
                    ep = m.group(4)
                else:  # juste la saison
                    m = re.search('( S|saison)(\s?|\.)(\d+)', sTitle, re.UNICODE | re.IGNORECASE)
                    if m:
                        sa = m.group(3)
    
            if sa:
                saisons.add(int(sa))
    
        # plusieurs saisons, on les découpe
        if len(saisons) > 0:
            oOutputParameterHandler = cOutputParameterHandler()
            for saison in saisons:
                sUrl = sSiteUrl + '&sSeason=%d' % saison
                sTitle = 'Saison %d ' % saison + sMovieTitle
                oOutputParameterHandler.addParameter('siteUrl', sUrl)
                oOutputParameterHandler.addParameter('sMovieTitle', sMovieTitle)
                oGui.addSeason(SITE_IDENTIFIER, 'showMedias', sTitle, '', '', '', oOutputParameterHandler)
            return nbFile
    
    # ajout des fichiers
    oOutputParameterHandler = cOutputParameterHandler()
    for file in content['files']:
        if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
            sTitle = file['file_name']
        else:
            sTitle = file['file_name'].encode('utf-8')
            
        sHosterUrl = URL_MAIN + file['file_code']
        
        
        # Recherche saisons et episodes
        sa = ep =''
        m = re.search('(|S|saison)(\s?|\.)(\d+)(\s?|\.)(E|Ep|x|\wpisode)(\s?|\.)(\d+)', sTitle.upper(), re.UNICODE | re.IGNORECASE)
        if m:
            sa = m.group(3)
            ep = m.group(7)
        else:  # Juste l'épisode
            m = re.search('(^|\s|\.)(E|Ep|\wpisode)(\s?|\.)(\d+)', sTitle, re.UNICODE | re.IGNORECASE)
            if m:
                ep = m.group(4)
            else:  # juste la saison
                m = re.search('( S|saison)(\s?|\.)(\d+)', sTitle, re.UNICODE | re.IGNORECASE)
                if m:
                    sa = m.group(3)

        if sSeason:
            if sa:
                if int(sa) != int(sSeason):
                    continue
            else:
                sa = sSeason
        
        if ep:
            sTitle = 'E' + ep + ' ' + sMovieTitle
            if sa:
                sTitle = 'S' + sa + sTitle
        
        nbFile += 1
        oOutputParameterHandler.addParameter('siteUrl', sHosterUrl)
        oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
        oGui.addEpisode(SITE_IDENTIFIER, 'showHosters', sTitle, '', '', '', oOutputParameterHandler)
        
    return nbFile

    

def showHosters():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sHosterUrl = oInputParameterHandler.getValue('siteUrl')
    sTitle = oInputParameterHandler.getValue('sMovieTitle')
    oHoster = cHosterGui().checkHoster(sHosterUrl)
    if oHoster != False:
        oHoster.setDisplayName(sTitle)
        oHoster.setFileName(sTitle)
        cHosterGui().showHoster(oGui, oHoster, sHosterUrl, '')
    oGui.setEndOfDirectory()



def getTag(sMovieTitle, tags, pos):
    for t in tags:
        aResult = re.search(t, sMovieTitle, re.IGNORECASE)
        if aResult:
            l = len(aResult.groups())
            ret = aResult[l]
            p = sMovieTitle.index(aResult[0])
            if p<pos:
                pos = p
            return ret.upper(), pos
    return False, pos



def getpath(content):
    for x in content:
        if x == 'path':
            sPath = Quote(content[x].encode('utf-8')).replace('//', '%2F%2F')
            return sPath


def AddmyAccount():
    upToMyAccount()


def upToMyAccount():
    addons = addon()

    if (addons.getSetting('hoster_uptobox_username') == '') and (addons.getSetting('hoster_uptobox_password') == ''):
        return
    oInputParameterHandler = cInputParameterHandler()
    sMediaUrl = oInputParameterHandler.getValue('sMediaUrl')

    oPremiumHandler = cPremiumHandler('uptobox')

    sHtmlContent = oPremiumHandler.GetHtml(URL_MAIN)
    cookies = GestionCookie().Readcookie('uptobox')

    aResult = re.search('<form id="fileupload" action="([^"]+)"', sHtmlContent, re.DOTALL)
    if aResult:
        upUrl = aResult.group(1).replace('upload?', 'remote?')

        if upUrl.startswith('//'):
            upUrl = 'https:' + upUrl

        fields = {'urls': '["' + sMediaUrl + '"]'}
        mpartdata = list(MPencode(fields))

        if isMatrix():
            mpartdata[1] = mpartdata[1].encode("utf-8")

        req = urllib2.Request(upUrl, mpartdata[1], headers)
        req.add_header('Content-Type', mpartdata[0].replace(',', ';'))
        req.add_header('Cookie', cookies)
        req.add_header('Content-Length', len(mpartdata[1]))

        # pénible ce dialog auth
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmcgui.Dialog().notification('Requête envoyée', 'vous pouvez faire autre chose', xbmcgui.NOTIFICATION_INFO, 4000, False)

        try:
            rep = urllib2.urlopen(req)
        except UrlError:
            return ''

        sHtmlContent = rep.read()
        rep.close()

        sPattern = '{"id":.+?,(?:"size":|"progress":)([0-9]+)'
        oParser = cParser()
        aResult = oParser.parse(sHtmlContent, sPattern)
        if aResult[0] is True:
            total = aResult[1][0]
            del aResult[1][0]

            dialog = xbmcgui.DialogProgressBG()
            dialog.create(SITE_NAME, 'Transfert de fichiers sur votre compte Uptobox')

            for aEntry in aResult[1]:
                if isMatrix():
                    dialog.update(int(aEntry) * 100 // int(total), 'Upload en cours...')
                else:
                    dialog.update(int(aEntry) * 100 / int(total), 'Upload en cours...')

                xbmc.sleep(500)
            dialog.close()

        else:
            # pénible ce dialog auth
            xbmc.executebuiltin('Dialog.Close(all,true)')
            xbmcgui.Dialog().notification('Info upload', 'Fichier introuvable', xbmcgui.NOTIFICATION_INFO, 2000, False)
    else:
        # pénible ce dialog auth
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmcgui.Dialog().notification('Info upload', 'Erreur pattern', xbmcgui.NOTIFICATION_ERROR, 2000, False)
