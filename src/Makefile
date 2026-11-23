#
# DCE3D Dreamcast 3D Engine (c)2013-2016 Josh PH3NOM Pearson
#

#Comipled .elf File Name
TARGET = dce.elf

#Compiler Optimization Flags
# GCC 14+ turns these into errors; the engine predates that and relies on the old behaviour
KOS_CFLAGS += -Wno-error=incompatible-pointer-types
# The engine uses GNU89 "inline" semantics (inline in header, definition in .c)
KOS_CFLAGS += -fgnu89-inline

KOS_CFLAGS += -ffast-math -O3 -fomit-frame-pointer -falign-loops=4 -falign-labels=4 -falign-functions=32 -falign-jumps=4 -Iinclude

#Engine Include Directory
KOS_CFLAGS += -I. -Idce/include/

#LDFLAGS=-Wl,-Map=output.map

#Engine C Source Code Files
OBJS = dce/dce-main.o dce/dce-input.o dce/dce-vector.o dce/dce-menu.o
OBJS += dce/dce-texture.o dce/dce-render.o
OBJS += dce/dce-collision.o
OBJS += dce/dce-animation.o dce/dce-timer.o dce/dce-decals.o dce/dce-sfx.o
OBJS += dce/dce-bbox.o dce/dce-init.o
OBJS += dce/dce-player.o dce/dce-gfx.o dce/dce-shader.o
OBJS += dce/dce-string.o dce/dce-rgb.o dce/dce-mat.o dce/dce-player-model.o dce/dce-rbo.o dce/dce-cbo.o
OBJS += dce/dce-enemy.o dce/dce-camera.o dce/dce-door.o dce/dce-trigger.o dce/dce-hud.o

#Engine Assembly Source Code Files
OBJS += dce/dce-clip-asm.o dce/dce-render-asm.o dce/dce-render-shadow.o dce/dce-collision-asm.o dce/dce-render-cull.o
OBJS += dce/dce-cull.o

#LibMPEG2 Decoder
KOS_CFLAGS += -I. -Ilibvdc/libmpeg2/include/

#LibMPG123 Decoder
KOS_CFLAGS += -I. -Ilibvdc/libmpg123/src/libmpg123/
OBJS += libvdc/snddrv.o
OBJS += libvdc/LibMPG123.o

#LibMPEG - MPEG Format Support
KOS_CFLAGS += -I. -Ilibvdc/
KOS_CFLAGS += -I. -Ilibvdc/libmpeg/
OBJS += libvdc/libmpeg/LibMPEG.o
OBJS += libvdc/LibMPEG2-Play.o
OBJS += libvdc/StreamBuffer.o libvdc/AudioStreamBuffer.o libvdc/StreamRender.o libvdc/GetTime.o


# Engine Font Utilities
KOS_CFLAGS += -I. -Ifont/
OBJS += font/font.o

# Quake 2 MD2 Interface
KOS_CFLAGS += -I. -Imd2/
OBJS += md2/md2.o

#Bundled decoder libraries (built with the current toolchain)
LIBMPEG2_DIR = libvdc/libmpeg2/libmpeg2
LIBMPG123_DIR = libvdc/libmpg123/libmpg123
LIBMPEG2 = $(LIBMPEG2_DIR)/libmpeg2.a
LIBMPG123 = $(LIBMPG123_DIR)/libmpg123_1.13.1.a

#Compile TARGET Elf
all: rm-elf $(TARGET)

.PHONY: all clean rm-elf run dist libs

libs:
	$(MAKE) -C $(LIBMPEG2_DIR)
	$(MAKE) -C $(LIBMPG123_DIR)

$(LIBMPEG2) $(LIBMPG123): libs

include $(KOS_BASE)/Makefile.rules

clean:
	-rm -f $(TARGET) $(OBJS)
	$(MAKE) -C $(LIBMPEG2_DIR) clean
	$(MAKE) -C $(LIBMPG123_DIR) clean

rm-elf:
	-rm -f $(TARGET)

$(TARGET): $(OBJS) $(LIBMPEG2) $(LIBMPG123)
	$(KOS_CC) $(KOS_CFLAGS) $(LDFLAGS) $(KOS_LDFLAGS) -o $(TARGET) $(KOS_START) \
		$(OBJS) $(OBJEXTRA) -L$(LIBMPEG2_DIR) -L$(LIBMPG123_DIR) \
		-ljpeg -lmpeg2 -lmpg123_1.13.1 -lm $(KOS_LIBS)

run: $(TARGET)
	$(KOS_LOADER) $(TARGET)

dist:
	rm -f $(OBJS)
	$(KOS_STRIP) $(TARGET)

