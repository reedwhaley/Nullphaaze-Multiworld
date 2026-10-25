OUTPUT_ARCH(powerpc:common)
ENTRY(payload_entry)

SECTIONS
{
    . = DEFINED(__payload_link_address) ? __payload_link_address : 0;

    .text : ALIGN(4)
    {
        KEEP(*(.text.payload))
        *(.text .text.*)
        *(.rodata .rodata.*)
        . = ALIGN(32);
        payload_embedded_runtime_start = .;
        KEEP(*(.data .data.*))
        payload_embedded_runtime_end = .;
        *(.bss .bss.* COMMON)
    }

    /DISCARD/ :
    {
        *(.comment)
        *(.eh_frame)
        *(.note*)
    }
}
