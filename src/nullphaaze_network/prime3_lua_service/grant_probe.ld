OUTPUT_ARCH(powerpc:common)
ENTRY(bridge_install)
SECTIONS
{
    . = 0x817e1000;
    .text : ALIGN(32)
    {
        KEEP(*(.text.bridge_install))
        KEEP(*(.text.bridge_boot))
        *(.text .text.*)
        *(.rodata .rodata.*)
        . = ALIGN(32);
    }
    .data : ALIGN(32)
    {
        KEEP(*(.data.grant_probe))
        . = ALIGN(32);
    }
    .bss : { *(.bss .bss.* .sbss .sbss.* COMMON) }
    ASSERT(SIZEOF(.data) == 32, "exact one-shot test receipt required")
    ASSERT(SIZEOF(.bss) == 0, "probe cannot depend on uninitialized BSS")
    ASSERT(. < 0x817ef000, "grant probe exceeds reserved region")
    /DISCARD/ : { *(.comment .eh_frame .note*) }
}
