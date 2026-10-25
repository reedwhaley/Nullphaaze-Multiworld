OUTPUT_ARCH(powerpc:common)
ENTRY(bridge_install)
SECTIONS {
    . = 0x817c1000;
    .text : ALIGN(32) {
        KEEP(*(.text.bridge_install)) KEEP(*(.text.bridge_boot))
        *(.text .text.* .rodata .rodata.*)
        . = ALIGN(32);
    }
    .data : ALIGN(32) {
        KEEP(*(.data.readiness))
        *(.data .data.* .sdata .sdata.*)
        . = ALIGN(32);
    }
    .bss : { *(.bss .bss.* .sbss .sbss.* COMMON) }
    ASSERT(SIZEOF(.bss) == 0, "diagnostic state must be explicitly initialized")
    ASSERT(. < 0x817cf000, "readiness diagnostic exceeds its isolated budget")
    /DISCARD/ : { *(.comment .eh_frame .note*) }
}
