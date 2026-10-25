/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef NULLPHAAZE_FRAME_POLL_H
#define NULLPHAAZE_FRAME_POLL_H
/* Preserve the established two-Hz IOS state-machine cadence independently of
   gameplay delta time, pause state, room ownership and Lua availability. */
static int mw_frame_poll_due(unsigned long long now,unsigned long long last,
                             unsigned int clock,unsigned int started) {
    if(clock<100000000u || clock>400000000u) return 0;
    return !started || now<last || now-last >= (unsigned long long)clock/8u;
}
#endif
