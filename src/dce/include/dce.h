/* 
** DCE - Dreamcast Engine (C) 2013-2016 Josh PH3NOM Pearson
*/

#ifndef DCE_H
#define DCE_H

#include <kos.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dc/fmath.h>
#include <dc/matrix.h>
#include <dc/matrix3d.h>
#include <dc/pvr.h>
#include <dc/vec3f.h>
#include <dc/video.h>
#include <dc/maple/controller.h>
#include <dc/maple/purupuru.h>

#include "dce-animation.h"
#include "dce-bbox.h"
#include "dce-camera.h"
#include "dce-collision.h"
#include "dce-decals.h"
#include "dce-door.h"
#include "dce-gfx.h"
#include "dce-hud.h"
#include "dce-init.h"
#include "dce-input.h"
#include "dce-matrix.h"
#include "dce-menu.h"
#include "dce-obj.h"
#include "dce-player.h"
#include "dce-player-model.h"
#include "dce-portal.h"
#include "dce-render.h"
#include "dce-rgb.h"
#include "dce-script.h"
#include "dce-shader.h"
#include "dce-sfx.h"
#include "dce-skybox.h"
#include "dce-texture.h"
#include "dce-timer.h"
#include "dce-trigger.h"
#include "dce-vector.h"
#include "dce-waypoint.h"
#include "dce-render-object.h"
#include "dce-enemy.h"

#include "font.h"
#include "md2.h"

#define DCE_TRIGGER_DISTANCE 30.0f

int DCE_RunLevel(char * map);
int DCE_RestartLevel(char * null);

void DCE_StringCopyNoExt(char * dst, char * src);
void DCE_StringCopyNewExt(char * dst, char * src, char * ext);
unsigned char DCE_StringHasExt(char * src, char * ext);
uint16_t DCE_StringFindCharFirst(char * string, char c);
unsigned char DCE_StringEqualsIgnoreCase(char * src, char * dst);

void DCE_PreComputeMD2VertexFlags();
void DCE_PlayerCollisionCallback(DCE_Player * player);

void DCE_RenderHurtScreenEffect(unsigned char id, unsigned char frames);

/* Functions defined in one module and used by others */
void DCE_RenderCallback(DCE_Player * player, DCE_Camera * cam, float t);
void DCE_RenderCallbackOP(DCE_Player * player, DCE_Camera * cam, float t, uint8_t index);
void DCE_RenderCallbackPT(DCE_Player * player, DCE_Camera * cam, float t, uint8_t index);
void DCE_RenderCallbackTR(DCE_Player * player, DCE_Camera * cam, float t, uint8_t index);
void DCE_PlayerFrameCallback(DCE_Player * player, DCE_Camera * cam, uint8_t index);
void DCE_PlayerTracePlayerRay(DCE_Player * player);
void DCE_RenderEnemyLOD(DCE_Player * player, DCE_Player * player2);
void DCE_RenderModelPlayerTR(DCE_Player * player);
void DCE_RenderMD2ComputeMatrixS(DCE_Player * player, struct hqmd2_frame_t *pframe, float r);
void DCE_SetCBOIndex(unsigned char index);
unsigned char DCE_LoadCBOInstance(char * fname, unsigned char active, char * segment,
                                  DCE_RenderObjectInstance * instance, unsigned char instances);
void DCE_LoadCBOCluster(char * fname);
void DCE_LoadRBOBatch(char * fname);
void DCE_LoadEnemyModels();
unsigned char DCE_ShaderParseToken(char * buf);
int DCE_InputCallbackWaitHack(DCE_Player * p);
void DCE_RunExecutionSequence(DCE_Player * p, DCE_Camera * c);
void DCE_SetVolumeCDDA(unsigned char vol);

#endif
