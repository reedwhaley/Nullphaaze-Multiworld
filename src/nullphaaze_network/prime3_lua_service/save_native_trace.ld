OUTPUT_ARCH(powerpc:common)
ENTRY(bridge_install)
SECTIONS
{
    . = 0x817e1000;
    .text : ALIGN(32)
    {
        KEEP(*(.text.bridge_install))
        KEEP(*(.text.bridge_boot))
        KEEP(*(.text.save_trace_hooks))
        *(.text .text.*)
        *(.rodata .rodata.*)
        . = ALIGN(32);
    }
    .data : ALIGN(32)
    {
        KEEP(*(.data.save_native_trace))
        . = ALIGN(32);
    }
    .bss : { *(.bss .bss.* .sbss .sbss.* COMMON) }
    ASSERT(SIZEOF(.data) == 8224, "exact diagnostic trace buffer required")
    ASSERT(SIZEOF(.bss) == 0, "trace cannot depend on uninitialized BSS")
    ASSERT(. < 0x817ef000, "trace exceeds reserved region")
    /DISCARD/ : { *(.comment .eh_frame .note*) }
}
