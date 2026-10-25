.section .rodata.network_save_profile,"a",@progbits
.balign 4
.global network_save_profile
network_save_profile:
.incbin NETWORK_SAVE_PROFILE_BINARY
