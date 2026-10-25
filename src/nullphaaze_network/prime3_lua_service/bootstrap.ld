OUTPUT_ARCH(powerpc:common)
ENTRY(payload_entry)
SECTIONS
{
    . = 0x806843c0;
    .text : ALIGN(32)
    {
        *(.text.payload)
        *(.rodata.bridge_blob)
        . = ALIGN(32);
    }
    ASSERT(. < 0x81100000, "staging code exceeds retail apploader boundary")
    /DISCARD/ : { *(.comment .eh_frame .note*) }
}
