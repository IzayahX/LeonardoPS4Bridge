/* Fixed-size unsigned 8-bit multiply/add rows for ATmega32U4.
 * AVR-GCC ABI: t=r25:r24, a=r23:r22, scalar=r20, return=r24.
 * r1 is restored to zero before return. Interrupts remain enabled.
 */
.section .text.avr_mac128,"ax",@progbits
.global avr_mac128
.type avr_mac128, @function
avr_mac128:
    movw r26, r24
    movw r30, r22
    clr  r22
    clr  r21
    ldi  r18, 128
1:
    ld   r19, Z+
    mul  r19, r20
    ld   r19, X
    add  r0, r19
    adc  r1, r22
    add  r0, r21
    adc  r1, r22
    st   X+, r0
    mov  r21, r1
    dec  r18
    brne 1b
    mov  r24, r21
    clr  r1
    ret
.size avr_mac128, .-avr_mac128

.section .text.avr_mac_shift128,"ax",@progbits
.global avr_mac_shift128
.type avr_mac_shift128, @function
avr_mac_shift128:
    push r28
    push r29
    movw r26, r24
    movw r28, r24
    movw r30, r22
    clr  r22

    /* First result byte is discarded; preserve its carry. */
    ld   r19, Z+
    mul  r19, r20
    ld   r19, X+
    add  r0, r19
    adc  r1, r22
    mov  r21, r1
    ldi  r18, 127
2:
    ld   r19, Z+
    mul  r19, r20
    ld   r19, X+
    add  r0, r19
    adc  r1, r22
    add  r0, r21
    adc  r1, r22
    st   Y+, r0
    mov  r21, r1
    dec  r18
    brne 2b
    mov  r24, r21
    clr  r1
    pop  r29
    pop  r28
    ret
.size avr_mac_shift128, .-avr_mac_shift128

/* One fused operand/reduction row. AVR-GCC arguments:
 * t=r25:r24, a=r23:r22, modulus=r21:r20, scalar=r18, m0inv=r16.
 * r16 is call-saved and remains untouched. Y is saved/restored.
 * X walks a, Z walks modulus, Y addresses the previous output limb.
 * r23=zero, r25=operand carry, r24=operand low byte,
 * r20=reduction carry, r21=reduction scalar, r19=loop count.
 * Interrupts remain enabled; normal AVR-GCC ISRs preserve SREG and r1.
 */
.section .text.avr_fios128,"ax",@progbits
.global avr_fios128
.type avr_fios128, @function
avr_fios128:
    push r28
    push r29
    movw r28, r24
    movw r26, r22
    movw r30, r20
    clr  r23

    /* First operand limb: s = t[0] + a[0]*scalar. */
    ld   r22, X+
    mul  r22, r18
    ld   r22, Y
    add  r0, r22
    adc  r1, r23
    movw r24, r0

    /* u = low(s)*m0inv; the first reduction byte is exactly zero. */
    mul  r0, r16
    mov  r21, r0
    ld   r22, Z+
    mul  r22, r21
    add  r0, r24
    adc  r1, r23
    mov  r20, r1
    ldi  r19, 127
3:
    /* Read old t[j] before replacing t[j-1]. */
    ld   r22, X+
    mul  r22, r18
    ldd  r22, Y+1
    add  r0, r22
    adc  r1, r23
    add  r0, r25
    adc  r1, r23
    movw r24, r0

    ld   r22, Z+
    mul  r22, r21
    add  r0, r24
    adc  r1, r23
    add  r0, r20
    adc  r1, r23
    st   Y+, r0
    mov  r20, r1
    dec  r19
    brne 3b

    /* Y=t+127. Fold both independent carries into old t[128]. */
    ldd  r22, Y+1
    clr  r24
    add  r22, r25
    adc  r24, r23
    add  r22, r20
    adc  r24, r23
    st   Y+, r22
    st   Y+, r24
    st   Y, r23
    clr  r1
    pop  r29
    pop  r28
    ret
.size avr_fios128, .-avr_fios128

/* Same row and ABI, with 31 groups of four limbs plus three tail limbs.
 * Keep the original symbol intact for independent benchmark comparisons.
 */
.section .text.avr_fios128_unrolled4,"ax",@progbits
.global avr_fios128_unrolled4
.type avr_fios128_unrolled4, @function
avr_fios128_unrolled4:
    push r28
    push r29
    movw r28, r24
    movw r26, r22
    movw r30, r20
    clr  r23

    ld   r22, X+
    mul  r22, r18
    ld   r22, Y
    add  r0, r22
    adc  r1, r23
    movw r24, r0

    mul  r0, r16
    mov  r21, r0
    ld   r22, Z+
    mul  r22, r21
    add  r0, r24
    adc  r1, r23
    mov  r20, r1
    ldi  r19, 31
4:
    .rept 4
    ld   r22, X+
    mul  r22, r18
    ldd  r22, Y+1
    add  r0, r22
    adc  r1, r23
    add  r0, r25
    adc  r1, r23
    movw r24, r0

    ld   r22, Z+
    mul  r22, r21
    add  r0, r24
    adc  r1, r23
    add  r0, r20
    adc  r1, r23
    st   Y+, r0
    mov  r20, r1
    .endr
    dec  r19
    /* Four bodies exceed BRNE's 64-word backward reach. */
    breq 5f
    rjmp 4b
5:
    .rept 3
    ld   r22, X+
    mul  r22, r18
    ldd  r22, Y+1
    add  r0, r22
    adc  r1, r23
    add  r0, r25
    adc  r1, r23
    movw r24, r0

    ld   r22, Z+
    mul  r22, r21
    add  r0, r24
    adc  r1, r23
    add  r0, r20
    adc  r1, r23
    st   Y+, r0
    mov  r20, r1
    .endr

    ldd  r22, Y+1
    clr  r24
    add  r22, r25
    adc  r24, r23
    add  r22, r20
    adc  r24, r23
    st   Y+, r22
    st   Y+, r24
    st   Y, r23
    clr  r1
    pop  r29
    pop  r28
    ret
.size avr_fios128_unrolled4, .-avr_fios128_unrolled4

/* Eight-limb unroll: 15 groups plus seven tail limbs. */
.section .text.avr_fios128_unrolled8,"ax",@progbits
.global avr_fios128_unrolled8
.type avr_fios128_unrolled8, @function
avr_fios128_unrolled8:
    push r28
    push r29
    movw r28, r24
    movw r26, r22
    movw r30, r20
    clr  r23

    ld   r22, X+
    mul  r22, r18
    ld   r22, Y
    add  r0, r22
    adc  r1, r23
    movw r24, r0

    mul  r0, r16
    mov  r21, r0
    ld   r22, Z+
    mul  r22, r21
    add  r0, r24
    adc  r1, r23
    mov  r20, r1
    ldi  r19, 15
4:
    .rept 8
    ld   r22, X+
    mul  r22, r18
    ldd  r22, Y+1
    add  r0, r22
    adc  r1, r23
    add  r0, r25
    adc  r1, r23
    movw r24, r0

    ld   r22, Z+
    mul  r22, r21
    add  r0, r24
    adc  r1, r23
    add  r0, r20
    adc  r1, r23
    st   Y+, r0
    mov  r20, r1
    .endr
    dec  r19
    /* Eight bodies exceed BRNE's 64-word backward reach. */
    breq 5f
    rjmp 4b
5:
    .rept 7
    ld   r22, X+
    mul  r22, r18
    ldd  r22, Y+1
    add  r0, r22
    adc  r1, r23
    add  r0, r25
    adc  r1, r23
    movw r24, r0

    ld   r22, Z+
    mul  r22, r21
    add  r0, r24
    adc  r1, r23
    add  r0, r20
    adc  r1, r23
    st   Y+, r0
    mov  r20, r1
    .endr

    ldd  r22, Y+1
    clr  r24
    add  r22, r25
    adc  r24, r23
    add  r22, r20
    adc  r24, r23
    st   Y+, r22
    st   Y+, r24
    st   Y, r23
    clr  r1
    pop  r29
    pop  r28
    ret
.size avr_fios128_unrolled8, .-avr_fios128_unrolled8
