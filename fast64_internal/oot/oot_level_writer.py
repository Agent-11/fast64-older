from .oot_constants import *
from .oot_level import *
from .oot_collision import *
from .oot_geolayout_writer import *
from .oot_texscroll import *

from ..utility import *

from bpy.utils import register_class, unregister_class
from io import BytesIO
import bpy, bmesh, os, math, re, shutil

def createGeoFile(levelName, filepath):
	result = '#include <ultra64.h>\n' +\
		'#include "sm64.h"\n' +\
		'#include "geo_commands.h"\n\n' +\
		'#include "game/level_geo.h"\n' +\
		'#include "game/geo_misc.h"\n' +\
		'#include "game/camera.h"\n' +\
		'#include "game/moving_texture.h"\n' +\
		'#include "game/screen_transition.h"\n' +\
		'#include "game/paintings.h"\n\n' +\
		'#include "make_const_nonconst.h"\n\n' +\
		'#include "levels/' + levelName + '/header.h"\n\n'
	
	geoFile = open(filepath, 'w', newline = '\n')
	geoFile.write(result)
	geoFile.close()

def createLevelDataFile(levelName, filepath):
	result = '#include <ultra64.h>"\n' +\
		'#include "sm64.h"\n' +\
		'#include "surface_terrains.h"\n' +\
		'#include "moving_texture_macros.h"\n' +\
		'#include "level_misc_macros.h"\n' +\
		'#include "macro_preset_names.h"\n' +\
		'#include "special_preset_names.h"\n' +\
		'#include "textures.h"\n' +\
		'#include "dialog_ids.h"\n\n' +\
		'#include "make_const_nonconst.h"\n\n'
	
	levelDataFile = open(filepath, 'w', newline = '\n')
	levelDataFile.write(result)
	levelDataFile.close()

def createHeaderFile(levelName, filepath):
	result = '#ifndef ' + levelName.upper() + '_HEADER_H\n' +\
		'#define ' + levelName.upper() + '_HEADER_H\n\n' +\
		'#include "types.h"\n' +\
		'#include "game/moving_texture.h"\n\n' +\
		'extern const LevelScript level_' + levelName + '_entry[];\n\n' +\
		'#endif\n'

	headerFile = open(filepath, 'w', newline = '\n')
	headerFile.write(result)
	headerFile.close()

class CourseDefines:
	def __init__(self, headerInfo, courses, bonusCourses, originalData):
		self.headerInfo = headerInfo
		self.courses = courses
		self.bonusCourses = bonusCourses
		self.originalData = originalData

	def to_c(self):
		result = self.headerInfo
		result += macrosToString(self.courses, False, tabDepth = 0)
		result += 'DEFINE_COURSES_END()\n'
		result += macrosToString(self.bonusCourses, False, tabDepth = 0)
		return result
	
	def write(self, filepath):
		data = self.to_c()
		if data == self.originalData:
			return
		defineFile = open(filepath, 'w', newline = '\n')
		defineFile.write(data)
		defineFile.close()
	
	def getOrMakeMacroByCourseName(self, courseEnum, isBonus):
		for course in self.courses:
			if course[1][0] == courseEnum:
				return course
		for bonusCourse in self.bonusCourses:
			if bonusCourse[1][0] == courseEnum:
				return bonusCourse
		if not isBonus:
			macroCmd = ['DEFINE_COURSE', [
				courseEnum,
				'0x44444440'
			], '']

			self.courses.append(macroCmd)
			return macroCmd	

		else:
			macroCmd = ['DEFINE_BONUS_COURSE', [
				courseEnum,
				'0x44444440'
			], '']

			self.bonusCourses.append(macroCmd)
			return macroCmd	

class LevelDefines:
	def __init__(self, headerInfo, defineMacros, originalData):
		self.headerInfo = headerInfo
		self.defineMacros = defineMacros
		self.originalData = originalData
		self.newLevelAdded = False

	def to_c(self):
		result = self.headerInfo
		result += macrosToString(self.defineMacros, False, tabDepth = 0)
		return result
	
	def write(self, filepath, headerPath):
		data = self.to_c()
		if data == self.originalData:
			return
		defineFile = open(filepath, 'w', newline = '\n')
		defineFile.write(data)
		defineFile.close()

		# Headers won't be updated unless this file is touched
		if self.newLevelAdded:
			os.utime(headerPath)

	def getOrMakeMacroByLevelName(self, levelName):
		for macro in self.defineMacros:
			if macro[0] == 'DEFINE_LEVEL' and macro[1][3] == levelName:
				return macro
		macroCmd = ['DEFINE_LEVEL', [
			'"' + levelName.upper() + '"', 
			'LEVEL_' + levelName.upper(), 
			'COURSE_' + levelName.upper(),
			levelName,
			'generic',
			'20000',
			'0x00',
			'0x00',
			'0x00',
			'_',
			'_'
		], '']
		self.newLevelAdded = True
		self.defineMacros.append(macroCmd)
		return macroCmd

class LevelScript:
	def __init__(self, name):
		self.name = name
		self.segmentLoads = []
		self.mario = 'MARIO(MODEL_MARIO, 0x00000001, bhvMario),'
		self.levelFunctions = []
		self.modelLoads = []
		self.actorIncludes = []
		self.marioStart = None
	
	def to_c(self, areaString):
		result = '#include <ultra64.h>\n' +\
			'#include "sm64.h"\n' +\
			'#include "behavior_data.h"\n' +\
			'#include "model_ids.h"\n' +\
			'#include "seq_ids.h"\n' +\
			'#include "dialog_ids.h"\n' +\
			'#include "segment_symbols.h"\n' +\
			'#include "level_commands.h"\n\n' +\
			'#include "game/level_update.h"\n\n' +\
			'#include "levels/scripts.h"\n\n'
		
		for actorInclude in self.actorIncludes:
			result += actorInclude + '\n'
		
		result += '\n#include "make_const_nonconst.h"\n'
		result += '#include "levels/' + self.name + '/header.h"\n\n'
		result += 'const LevelScript level_' + self.name + '_entry[] = {\n'
		result += '\tINIT_LEVEL(),\n'
		for segmentLoad in self.segmentLoads:
			result += '\t' + macroToString(segmentLoad, True) + '\n'
		result += '\tALLOC_LEVEL_POOL(),\n'
		result += '\t' + self.mario + '\n'
		for levelFunction in self.levelFunctions:
			result += '\t' + macroToString(levelFunction, True) + '\n'
		for modelLoad in self.modelLoads:
			result += '\t' + macroToString(modelLoad, True) + '\n'
		result += '\n'

		result += areaString

		result += '\tFREE_LEVEL_POOL(),\n'
		if self.marioStart is not None:
			result += '\t' + self.marioStart.to_c() + ',\n'
		else:
			result += '\tMARIO_POS(1, 0, 0, 0, 0),\n'
		result += \
		    '\tCALL(0, lvl_init_or_update),\n' +\
		    '\tCALL_LOOP(1, lvl_init_or_update),\n' +\
		    '\tCLEAR_LEVEL(),\n' +\
		    '\tSLEEP_BEFORE_EXIT(1),\n' +\
		    '\tEXIT(),\n};\n'
		
		return result

def parseCourseDefines(filepath):
	if not os.path.exists(filepath):
		raise PluginError("Path \"" + filepath + '" does not exist, could not read course defines file.')
	scriptFile = open(filepath, 'r', newline = '\n')
	scriptData = scriptFile.read()
	scriptFile.close()

	matchResult = re.search('(\w*)\((((?!\)).)+)\)', scriptData, re.DOTALL)
	if matchResult is None:
		raise PluginError("Path \"" + filepath + '" does not have any course define macros in it.')
	headerInfo = scriptData[:matchResult.start(0)]
	defineMacros = stringToMacros(scriptData)
	courses = []
	bonusCourses = []

	for macro in defineMacros:
		if macro[0] == 'DEFINE_COURSE':
			courses.append(macro)
		elif macro[0] == 'DEFINE_BONUS_COURSE':
			bonusCourses.append(macro)

	return CourseDefines(headerInfo, courses, bonusCourses, scriptData)

def parseLevelDefines(filepath):
	if not os.path.exists(filepath):
		raise PluginError("Path \"" + filepath + '" does not exist, could not read level defines file.')
	scriptFile = open(filepath, 'r', newline = '\n')
	scriptData = scriptFile.read()
	scriptFile.close()

	matchResult = re.search('(\w*)\((((?!\)).)*)\)', scriptData, re.DOTALL)
	if matchResult is None:
		raise PluginError("Path \"" + filepath + '" does not have any level define macros in it.')
	headerInfo = scriptData[:matchResult.start(0)]
	defineMacros = stringToMacros(scriptData)

	return LevelDefines(headerInfo, defineMacros, scriptData)

def parseZoomMasks(filepath):
	if not os.path.exists(filepath):
		raise PluginError("Path \"" + filepath + '" does not exist, could not read camera.c file.')
	cameraFile = open(filepath, 'r', newline = '\n')
	cameraData = cameraFile.read()
	cameraFile.close()

	matchResult = re.search('u8\s*sZoomOutAreaMasks\s*\[\]\s*=\s*\{' +\
		'(((?!\}).)*)\}\s*;', cameraData, re.DOTALL)
	
	if matchResult is None:
		raise PluginError("Could not find sZoomOutAreaMasks in \"" + filepath + '".')

	zoomMaskString = matchResult.group(1)
	zoomMacros = stringToMacros(zoomMaskString)

	return ZoomOutMasks(zoomMacros, cameraData)

def replaceSegmentLoad(levelscript, segmentName, command, changedSegment):
	changedLoad = None
	for segmentLoad in levelscript.segmentLoads:
		segmentString = segmentLoad[1][0].lower()
		segment = int(segmentString, 16 if 'x' in segmentString else 10)
		if segmentLoad[0] == command and segment == changedSegment:
			changedLoad = segmentLoad
	if changedLoad is None:
		changedLoad = [command, [hex(changedSegment), '', ''], '']
		levelscript.segmentLoads.append(changedLoad)
	
	changedLoad[1][1] = segmentName + 'SegmentRomStart'
	changedLoad[1][2] = segmentName + 'SegmentRomEnd'

def stringToMacros(data):
	macroData = []
	for matchResult in re.finditer('(\w*)\((((?!\)).)*)\),?(((?!\n)\s)*\/\/((?!\n).)*)?', data):
		macro = matchResult.group(1)
		arguments = matchResult.group(2)
		if matchResult.group(4) is not None:
			comment = matchResult.group(4).strip()
		else:
			comment = ''
		arguments = re.sub('\/\*(\*(?!\/)|[^*])*\*\/', '', arguments)
		arguments = arguments.split(',')
		for i in range(len(arguments)):
			arguments[i] = arguments[i].strip()
		
		macroData.append([macro, arguments, comment])
	
	return macroData

def macroToString(macroCmd, useComma):
	result = macroCmd[0] + '('
	for arg in macroCmd[1]:
		result += arg + ', '
	result = result[:-2] + ')' + (',' if useComma else '')
	result += " " + macroCmd[2]
	return result

def macrosToString(macroCmds, useComma, tabDepth = 1):
	result = ''
	for macroCmd in macroCmds:
		result += '\t' * tabDepth + macroToString(macroCmd, useComma) + '\n'
	return result

def setStartLevel(basePath, levelEnum):
	filepath = os.path.join(basePath, 'levels/menu/script.c')
	data = getDataFromFile(filepath)

	newData = re.sub('SET\_REG\((((?!\)).)*)\)', 'SET_REG(' + levelEnum + ')', data, count = 1)
	if newData != data:
		saveDataToFile(filepath, newData)


def addActSelectorIgnore(basePath, levelEnum):
	filepath = os.path.join(basePath, 'src/game/level_update.c')
	data = getDataFromFile(filepath)

	checkResult = re.search('if\s*\(gCurrLevelNum\s*==\s*' + levelEnum + '\)\s*return\s*0;', data, re.DOTALL)
	if checkResult is not None:
		return

	# This won't actually match whole function, but only up to first closing bracket.
	# This should be okay though... ?	
	matchResultFunction = re.search('s32\s*lvl\_set\_current\_level\s*\((((?!\)).)*)\)\s*\{' +\
		'(((?!\}).)*)\}', data, re.DOTALL)
	
	if matchResultFunction is None:
		raise PluginError("Could not find lvl_set_current_level in \"" + filepath + '".')

	functionContents = matchResultFunction.group(3)

	matchResult = re.search('gCurrCourseNum\s*\=\s*gLevelToCourseNumTable(((?!\;).)*)\;', functionContents, re.DOTALL)
	if matchResult is None:
		raise PluginError("Could not find gCurrCourseNum setting in lvl_set_current_level in \"" + filepath + '".')

	functionContents = functionContents[:matchResult.end(0)] + \
		'\n\tif (gCurrLevelNum == ' + levelEnum + ') return 0;' +\
		functionContents[matchResult.end(0):]

	newData = data[:matchResultFunction.start(3)] + functionContents + data[matchResultFunction.end(3):]

	saveDataToFile(filepath, newData)

def removeActSelectorIgnore(basePath, levelEnum):
	filepath = os.path.join(basePath, 'src/game/level_update.c')
	data = getDataFromFile(filepath)

	newData = re.sub('if\s*\(gCurrLevelNum\s*\=\=\s*' + levelEnum + '\)\s*return\s*0\;\n', '', data, re.DOTALL)
	if data != newData:
		saveDataToFile(filepath, newData)

def parseLevelScript(filepath, levelName):
	scriptPath = os.path.join(filepath, 'script.c')
	scriptData = getDataFromFile(scriptPath)
	
	levelscript = LevelScript(levelName)

	for matchResult in re.finditer('#include\s*"actors/(\w*)\.h"', scriptData):
		levelscript.actorIncludes.append(matchResult.group(0))

	matchResult = re.search('const\s*LevelScript\s*level\_\w*\_entry\[\]\s*=\s*\{' +\
		'(((?!\}).)*)\}\s*;', scriptData, re.DOTALL)
	
	if matchResult is None:
		raise PluginError("Could not find entry levelscript in \"" + scriptPath + '".')

	scriptContents = matchResult.group(1)

	macroData = stringToMacros(scriptContents)
	inArea = False
	for macroCmd in macroData:
		if not inArea:
			if macroCmd[0] == 'LOAD_MIO0' or \
				macroCmd[0] == 'LOAD_MIO0_TEXTURE' or \
				macroCmd[0] == 'LOAD_YAY0' or \
				macroCmd[0] == 'LOAD_YAY0_TEXTURE' or \
				macroCmd[0] == 'LOAD_RAW':
				levelscript.segmentLoads.append(macroCmd)
			elif macroCmd[0] == 'JUMP_LINK':
				levelscript.levelFunctions.append(macroCmd)
			elif macroCmd[0] == 'LOAD_MODEL_FROM_GEO':
				levelscript.modelLoads.append(macroCmd)
			elif macroCmd[0] == 'MARIO':
				levelscript.mario = macroToString(macroCmd, True)
		
		if macroCmd[0] == 'AREA':
			inArea = True
		elif macroCmd[0] == 'END_AREA':
			inArea = False
		
	return levelscript
	
def ootExportLevelC(obj, transformMatrix, f3dType, isHWv1, levelName, exportDir,
	savePNG, customExport, DLFormat):
	
	if customExport:
		levelDir = os.path.join(exportDir, levelName)
	else:
		levelDir = os.path.join(exportDir, 'levels/' + levelName)
		
	if customExport or not os.path.exists(os.path.join(levelDir, 'script.c')):
		prevLevelScript = LevelScript(levelName)
	else:
		prevLevelScript = parseLevelScript(levelDir, levelName)

	if not os.path.exists(levelDir):
		os.mkdir(levelDir)
	areaDict = {}

	geoString = ''
	levelDataString = ''
	headerString = ''
	areaString = ''
	cameraVolumeString = "struct CameraTrigger " + levelCameraVolumeName + "[] = {\n"

	fModel = FModel(f3dType, isHWv1, levelName + '_dl', DLFormat)
	childAreas = [child for child in obj.children if child.data is None and child.sm64_obj_type == 'Area Root']
	if len(childAreas) == 0:
		raise PluginError("The level root has no child empties with the 'Area Root' object type.")

	usesEnvFX = False
	echoLevels = ['0x00', '0x00', '0x00']
	zoomFlags = [False, False, False, False]
	for child in childAreas:
		if len(child.children) == 0:
			raise PluginError("Area for " + child.name + " has no children.")
		if child.areaIndex in areaDict:
			raise PluginError(child.name + " shares the same area index as " + areaDict[child.areaIndex].name)
		#if child.areaCamera is None:
		#    raise PluginError(child.name + ' does not have an area camera set.')
		#setOrigin(obj, child)
		areaDict[child.areaIndex] = child
		
		areaIndex = child.areaIndex
		areaName = 'area_' + str(areaIndex)
		areaDir = os.path.join(levelDir, areaName)
		if not os.path.exists(areaDir):
			os.mkdir(areaDir)

		envOption = child.envOption if child.envOption != 'Custom' else child.envType
		usesEnvFX |= envOption != 'ENVFX_MODE_NONE'

		if child.areaIndex == 1 or child.areaIndex == 2 or child.areaIndex == 3:
			echoLevels[child.areaIndex - 1] = child.echoLevel
		if child.areaIndex == 1 or child.areaIndex == 2 or child.areaIndex == 3 or child.areaIndex == 4:
			zoomFlags[child.areaIndex - 1] = child.zoomOutOnPause

		# Needs to be done BEFORE collision parsing
		setRooms(child)

		geolayoutGraph, fModel = \
			convertObjectToGeolayout(obj, transformMatrix, 
			f3dType, isHWv1, child.areaCamera, levelName + '_' + areaName, fModel, child, DLFormat, not savePNG)

		# Write geolayout
		geoFile = open(os.path.join(areaDir, 'geo.inc.c'), 'w', newline = '\n')
		geoFile.write(geolayoutGraph.to_c())
		geoFile.close()
		geoString += '#include "levels/' + levelName + '/' + areaName + '/geo.inc.c"\n'
		headerString += geolayoutGraph.to_c_def()

		# Write collision
		collision = \
			exportCollisionCommon(child, transformMatrix, True, True, 
				levelName + '_' + areaName, child.areaIndex)
		colFile = open(os.path.join(areaDir, 'collision.inc.c'), 'w', newline = '\n')
		colFile.write(collision.to_c())
		colFile.close()
		levelDataString += '#include "levels/' + levelName + '/' + areaName + '/collision.inc.c"\n'
		headerString += collision.to_c_def()

		# Write rooms
		if child.enableRoomSwitch:
			roomFile = open(os.path.join(areaDir, 'room.inc.c'), 'w', newline = '\n')
			roomFile.write(collision.to_c_rooms())
			roomFile.close()
			levelDataString += '#include "levels/' + levelName + '/' + areaName + '/room.inc.c"\n'
			headerString += collision.to_c_rooms_def()

		# Get area
		area = exportAreaCommon(child, transformMatrix, 
			geolayoutGraph.startGeolayout, collision, levelName + '_' + areaName)
		if area.mario_start is not None:
			prevLevelScript.marioStart = area.mario_start
		areaString += area.to_c_script(child.enableRoomSwitch)
		cameraVolumeString += area.to_c_camera_volumes()

		# Write macros
		macroFile = open(os.path.join(areaDir, 'macro.inc.c'), 'w', newline = '\n')
		macroFile.write(area.to_c_macros())
		macroFile.close()
		levelDataString += '#include "levels/' + levelName + '/' + areaName + '/macro.inc.c"\n'
		headerString += area.to_c_def_macros()

		# Write splines
		splineFile = open(os.path.join(areaDir, 'spline.inc.c'), 'w', newline = '\n')
		splineFile.write(area.to_c_splines())
		splineFile.close()
		levelDataString += '#include "levels/' + levelName + '/' + areaName + '/spline.inc.c"\n'
		headerString += area.to_c_def_splines()

	cameraVolumeString += '\tNULL_TRIGGER\n};'

	# Generate levelscript string
	compressionFmt = bpy.context.scene.compressionFormat
	replaceSegmentLoad(prevLevelScript, 
		'_' + levelName + '_segment_7', 'LOAD_' + compressionFmt.upper(), 0x07)
	if usesEnvFX:
		replaceSegmentLoad(prevLevelScript, 
			'_effect_' + compressionFmt, 'LOAD_' + compressionFmt.upper(), 0x0B)
	if not obj.useBackgroundColor:
		replaceSegmentLoad(prevLevelScript, 
			'_' + backgroundSegments[obj.background] + '_skybox_' + compressionFmt, 'LOAD_' + compressionFmt.upper(), 0x0A)
	levelscriptString = prevLevelScript.to_c(areaString)

	# Remove old areas.
	for f in os.listdir(levelDir):
		if re.search('area\_\d+', f):
			existingArea = False
			for index, areaObj in areaDict.items():
				if f == 'area_' + str(index):
					existingArea = True
			if not existingArea:
				shutil.rmtree(os.path.join(levelDir, f))
	
	gfxFormatter = SM64GfxFormatter(ScrollMethod.Vertex)
	static_data, dynamic_data, texC = fModel.to_c(savePNG, savePNG, 'levels/' + levelName, gfxFormatter)
	scroll_data, hasScrolling = fModel.to_c_vertex_scroll(levelName, gfxFormatter)
	headerStatic, headerDynamic = fModel.to_c_def(gfxFormatter)
	headerScroll = fModel.to_c_vertex_scroll_def(levelName, gfxFormatter)

	if savePNG:
		levelDataString =  '#include "levels/' + levelName + '/texture_include.inc.c"\n' + levelDataString
		fModel.save_textures(levelDir)

		texPath = os.path.join(levelDir, 'texture_include.inc.c')
		texFile = open(texPath, 'w', newline='\n')
		texFile.write(texC)
		texFile.close()

	
	modifyTexScrollFiles(exportDir, levelDir, headerScroll, scroll_data, hasScrolling)

	# Write materials
	if DLFormat == DLFormat.Static:
		static_data += dynamic_data
		headerStatic += headerDynamic
	else:
		geoString = writeMaterialFiles(exportDir, levelDir, 
			'#include "levels/' + levelName + '/header.h"', 
			'#include "levels/' + levelName + '/material.inc.h"',
			headerDynamic, dynamic_data, geoString, customExport)

	modelPath = os.path.join(levelDir, 'model.inc.c')
	modelFile = open(modelPath, 'w', newline='\n')
	modelFile.write(static_data)
	modelFile.close()

	fModel.freePalettes()

	levelDataString += '#include "levels/' + levelName + '/model.inc.c"\n'
	headerString += headerStatic
	#headerString += '\nextern const LevelScript level_' + levelName + '_entry[];\n'
	#headerString += '\n#endif\n'

	# Write geolayout
	geoFile = open(os.path.join(levelDir, 'geo.inc.c'), 'w', newline='\n')
	geoFile.write(geoString)
	geoFile.close()

	levelDataFile = open(os.path.join(levelDir, 'leveldata.inc.c'), 'w', newline='\n')
	levelDataFile.write(levelDataString)
	levelDataFile.close()

	headerFile = open(os.path.join(levelDir, 'header.inc.h'), 'w', newline='\n')
	headerFile.write(headerString)
	headerFile.close()

	scriptFile = open(os.path.join(levelDir, 'script.c'), 'w', newline = '\n')
	scriptFile.write(levelscriptString)
	scriptFile.close()

	if customExport:
		cameraVolumeString = '// Replace the level specific camera volume struct in src/game/camera.c with this.\n' +\
			'// Make sure to also add the struct name to the LEVEL_DEFINE in levels/level_defines.h.\n' +\
			cameraVolumeString
		cameraFile = open(os.path.join(levelDir, 'camera_trigger.inc.c'), 'w', newline='\n')
		cameraFile.write(cameraVolumeString)
		cameraFile.close()

	if not customExport:
		if DLFormat != DLFormat.Static:
			# Write material headers
			writeMaterialHeaders(exportDir,  
				'#include "levels/' + levelName + '/material.inc.c"',
				'#include "levels/' + levelName + '/material.inc.h"')

		# Export camera triggers
		cameraPath = os.path.join(exportDir, 'src/game/camera.c')
		overwriteData('struct\s*CameraTrigger\s*', levelCameraVolumeName, cameraVolumeString, cameraPath,
			'struct CameraTrigger *sCameraTriggers', False)

		levelHeadersPath = os.path.join(exportDir, 'levels/level_headers.h.in')
		levelDefinesPath = os.path.join(exportDir, 'levels/level_defines.h')
		levelDefines = parseLevelDefines(levelDefinesPath)
		levelDefineMacro = levelDefines.getOrMakeMacroByLevelName(levelName)
		levelIndex = levelDefines.defineMacros.index(levelDefineMacro)
		levelEnum = levelDefineMacro[1][levelDefineArgs['level enum']]

		levelDefineMacro[1][levelDefineArgs['camera table']] = levelCameraVolumeName
		levelDefineMacro[1][levelDefineArgs['acoustic reach']] = obj.acousticReach
		levelDefineMacro[1][levelDefineArgs['echo level 1']] = echoLevels[0]
		levelDefineMacro[1][levelDefineArgs['echo level 2']] = echoLevels[1]
		levelDefineMacro[1][levelDefineArgs['echo level 3']] = echoLevels[2] 

		levelDefines.write(levelDefinesPath, levelHeadersPath)

		courseDefinesPath = os.path.join(exportDir, 'levels/course_defines.h')
		courseDefines = parseCourseDefines(courseDefinesPath)
		courseEnum = levelDefineMacro[1][levelDefineArgs['course name']]
		courseMacro = courseDefines.getOrMakeMacroByCourseName(courseEnum, False)
		courseMacro[1][1] = obj.starGetCutscenes.value()
		courseDefines.write(courseDefinesPath)

		cameraPath = os.path.join(exportDir, 'src/game/camera.c')
		zoomMasks = parseZoomMasks(cameraPath)
		zoomMasks.updateMaskCount(len(levelDefines.defineMacros))
		zoomMasks.setMask(levelIndex, zoomFlags)
		zoomMasks.write(cameraPath)

		if obj.actSelectorIgnore:
			addActSelectorIgnore(exportDir, levelEnum)
		else:
			removeActSelectorIgnore(exportDir, levelEnum)

		if obj.setAsStartLevel:
			setStartLevel(exportDir, levelEnum)

		geoPath = os.path.join(levelDir, 'geo.c')
		levelDataPath = os.path.join(levelDir, 'leveldata.c')
		headerPath = os.path.join(levelDir, 'header.h')
		
		# Create files if not already existing
		if not os.path.exists(geoPath):
			createGeoFile(levelName, geoPath)
		if not os.path.exists(levelDataPath):
			createLevelDataFile(levelName, levelDataPath)
		if not os.path.exists(headerPath):
			createHeaderFile(levelName, headerPath)

		# Write level data		
		writeIfNotFound(geoPath, '#include "levels/' + levelName + '/geo.inc.c"\n', '')
		writeIfNotFound(levelDataPath, '#include "levels/' + levelName + '/leveldata.inc.c"\n', '')
		writeIfNotFound(headerPath, '#include "levels/' + levelName + '/header.inc.h"\n', '#endif')
		
		if not savePNG:
			textureIncludePath = os.path.join(levelDir, 'texture_include.inc.c')
			if os.path.exists(textureIncludePath):
				os.remove(textureIncludePath)
			# This one is for backwards compatibility purposes
			deleteIfFound(os.path.join(levelDir, 'texture.inc.c'), 
				'#include "levels/' + levelName + '/texture_include.inc.c"')
		
		# This one is for backwards compatibility purposes
		deleteIfFound(levelDataPath,
			'#include "levels/' + levelName + '/texture_include.inc.c"')
		
		texscrollIncludeC = '#include "levels/' + levelName + '/texscroll.inc.c"'
		texscrollIncludeH = '#include "levels/' + levelName + '/texscroll.inc.h"'
		texscrollGroup = levelName
		texscrollGroupInclude = '#include "levels/' + levelName + '/header.h"'

		modifyTexScrollHeadersGroup(exportDir, texscrollIncludeC, texscrollIncludeH, 
			texscrollGroup, headerScroll, texscrollGroupInclude, hasScrolling)

def addGeoC(levelName):
	header = \
		'#include <ultra64.h>\n' \
		'#include "sm64.h"\n' \
		'#include "geo_commands.h"\n' \
		'\n' \
		'#include "game/level_geo.h"\n' \
		'#include "game/geo_misc.h"\n' \
		'#include "game/camera.h"\n' \
		'#include "game/moving_texture.h"\n' \
		'#include "game/screen_transition.h"\n' \
		'#include "game/paintings.h"\n\n'
	
	header += '#include "levels/' + levelName + '/header.h"\n'
	return header

def addLevelDataC(levelName):
	header = \
		'#include <ultra64.h>\n' \
		'#include "sm64.h"\n' \
		'#include "surface_terrains.h"\n' \
		'#include "moving_texture_macros.h"\n' \
		'#include "level_misc_macros.h"\n' \
		'#include "macro_preset_names.h"\n' \
		'#include "special_preset_names.h"\n' \
		'#include "textures.h"\n' \
		'#include "dialog_ids.h"\n' \
		'\n' \
		'#include "make_const_nonconst.h"\n'
	
	return header

def addHeaderC(levelName):
	header = \
		'#ifndef ' + levelName.upper() + '_HEADER_H\n' +\
		'#define ' + levelName.upper() + '_HEADER_H\n' +\
		'\n' \
		'#include "types.h"\n' \
		'#include "game/moving_texture.h"\n\n'
	
	return header
	
class OOT_ExportLevel(bpy.types.Operator):
	# set bl_ properties
	bl_idname = 'object.oot_export_level'
	bl_label = "Export Level"
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

	def execute(self, context):
		try:
			if context.mode != 'OBJECT':
				raise PluginError("Operator can only be used in object mode.")
			if len(context.selected_objects) == 0:
				raise PluginError("Object not selected.")
			obj = context.selected_objects[0]
			if obj.data is not None or obj.ootObjType != 'Scene Root':
				raise PluginError("The selected object is not an empty with the Scene Root type.")

			#obj = context.active_object

			scaleValue = bpy.context.scene.ootBlenderScale
			finalTransform = mathutils.Matrix.Diagonal(mathutils.Vector((
				scaleValue, scaleValue, scaleValue))).to_4x4()
		
		except Exception as e:
			raisePluginError(self, e)
			return {'CANCELLED'} # must return a set
		try:
			applyRotation([obj], math.radians(90), 'X')
			if context.scene.ootlLevelCustomExport:
				exportPath = bpy.path.abspath(context.scene.ootLevelExportPath)
				levelName = context.scene.ootLevelName
			else:
				exportPath = bpy.path.abspath(context.scene.ootDecompPath)
				if context.scene.ootLevelOption == 'custom':
					levelName = context.scene.ootLevelName
				else:
					levelName = context.scene.ootLevelOption
			#if not context.scene.ootLevelCustomExport:
			#	applyBasicTweaks(exportPath)
			
			ootExportLevel(obj, finalTransform,
				context.scene.f3d_type, context.scene.isHWv1, levelName, exportPath, 
				context.scene.saveTextures or bpy.context.scene.ignoreTextureRestrictions, 
				context.scene.ootLevelCustomExport, DLFormat.Dynamic)
			self.report({'INFO'}, 'Success!')

			applyRotation([obj], math.radians(-90), 'X')
			#applyRotation(obj.children, math.radians(0), 'X')
			return {'FINISHED'} # must return a set

		except Exception as e:
			if context.mode != 'OBJECT':
				bpy.ops.object.mode_set(mode = 'OBJECT')

			applyRotation([obj], math.radians(-90), 'X')

			obj.select_set(True)
			context.view_layer.objects.active = obj
			raisePluginError(self, e)
			return {'CANCELLED'} # must return a set

class OOT_ExportLevelPanel(bpy.types.Panel):
	bl_idname = "OOT_PT_export_level"
	bl_label = "OOT Level Exporter"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'OOT'

	@classmethod
	def poll(cls, context):
		return True

	# called every frame
	def draw(self, context):
		col = self.layout.column()
		col.operator(OOT_ExportLevel.bl_idname)
		if not bpy.context.scene.ignoreTextureRestrictions:
			col.prop(context.scene, 'saveTextures')
		col.prop(context.scene, 'ootLevelCustomExport')
		if context.scene.ootLevelCustomExport:
			prop_split(col, context.scene, 'ootLevelExportPath', 'Directory')
			prop_split(col, context.scene, 'ootLevelName', 'Name')
			customExportWarning(col)
		else:
			col.prop(context.scene, 'ootLevelOption')
			if context.scene.ootLevelOption == 'custom':
				levelName = context.scene.ootLevelName
				box = col.box()
				#box.label(text = 'Adding levels may require modifying the save file format.')
				#box.label(text = 'Check src/game/save_file.c.')
				prop_split(col, context.scene, 'ootLevelName', 'Name')
			else:
				levelName = context.scene.ootLevelOption
		
		for i in range(panelSeparatorSize):
			col.separator()

oot_level_classes = (
	OOT_ExportLevel,
)

oot_level_panel_classes = (
	OOT_ExportLevelPanel,
)

def oot_level_panel_register():
	for cls in oot_level_panel_classes:
		register_class(cls)

def oot_level_panel_unregister():
	for cls in oot_level_panel_classes:
		unregister_class(cls)

def oot_level_register():
	for cls in oot_level_classes:
		register_class(cls)
	
	bpy.types.Scene.ootLevelName = bpy.props.StringProperty(name = 'Name', default = 'bob')
	bpy.types.Scene.ootLevelOption = bpy.props.EnumProperty(name = "Level", items = ootEnumLevelNames, default = 'bob')
	bpy.types.Scene.ootLevelExportPath = bpy.props.StringProperty(
		name = 'Directory', subtype = 'FILE_PATH')
	bpy.types.Scene.ootLevelCustomExport = bpy.props.BoolProperty(
		name = 'Custom Export Path')

def oot_level_unregister():
	for cls in reversed(oot_level_classes):
		unregister_class(cls)

	del bpy.types.Scene.ootlevelName
	del bpy.types.Scene.ootlevelExportPath
	del bpy.types.Scene.ootlevelCustomExport
	del bpy.types.Scene.ootlevelOption