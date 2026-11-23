#include <time.h>
#include <arch/timer.h>

#include "GetTime.h"

static uint32_t s, ms;
static uint64_t msec;

/* Get current hardware timing using arch/timer.h */
uint64_t GetTime()
{
    timer_ms_gettime(&s, &ms);
    msec = (((uint64_t)s) * ((uint64_t)1000)) + ((uint64_t)ms);
    return (unsigned int)msec;
}