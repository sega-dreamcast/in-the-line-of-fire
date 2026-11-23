/* 
** DCE - Dreamcast Engine (C) 2013-2015 Josh PH3NOM Pearson
*/

#include <time.h>
#include <arch/timer.h>

/* Get current hardware timing using arch/timer.h */
static uint32_t s, ms;
static uint64_t msec;

unsigned int DCE_GetTime()
{
   	timer_ms_gettime(&s, &ms);
	msec = (((uint64_t)s) * ((uint64_t)1000)) + ((uint64_t)ms);
	
	return (unsigned int)msec;
}
