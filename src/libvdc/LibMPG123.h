/*
**
** This file is a part of Dreamcast Media Center
** (C) Josh PH3NOM Pearson 2011-2013
**
*/
/*
**  LibMPG123 streaming decoder (C) Josh 'PH3NOM' Pearson
*/

#ifndef LibMPG123_H
#define LibMPG123_H

#include <kos/mutex.h>

extern volatile unsigned char MP3_NEED_SAMPLES;

int LibMPG123_Init();

int LibMPG123_DecodeChunk( uint8_t * mpabuf, int size );

int LibMPG123_Exit();

void LibMPG123_VolumeUp();

void LibMPG123_VolumeDown();

void LibMPG123_WaitStart();

void LibMPG123_Start();

#endif
