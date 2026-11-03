/* Single-frame separated Montgomery reduction for 1024-bit AVR operands.
 * The 9-byte accumulator remains in r10..r18 for all 64 columns. Native USB
 * interrupts stay enabled except during the two stack-pointer updates.
 */

#include <avr/io.h>

#define F_OUT_L      1
#define F_OUT_H      2
#define F_PRODUCT_L  3
#define F_PRODUCT_H  4
#define F_MODULUS_L  5
#define F_MODULUS_H  6
#define F_INVERSE_0  7
#define F_INVERSE_1  8
#define F_INVERSE_2  9
#define F_INVERSE_3 10
#define F_SCRATCH_L 11
#define F_SCRATCH_H 12
#define F_POINTER_L 13
#define F_POINTER_H 14
#define F_COLUMN    15
#define FRAME_SIZE  15

.macro RPS_GROUP alo, ahi, blo, bhi, z0, z1, z2, z3, catcher
    mul  \ahi, \bhi
    movw r24, r0

    mul  \alo, \bhi
    add  \z1, r0
    adc  r24, r1
    adc  r25, r23

    mul  \ahi, \blo
    add  \z1, r0
    adc  r24, r1
    adc  r25, r23

    mul  \alo, \blo
    add  \z0, r0
    adc  \z1, r1
    adc  \z2, r24
    adc  \z3, r25
    adc  \catcher, r23
.endm

.macro RPS_BLOCK
    ld   r2, X+
    ld   r3, X+
    ld   r4, X+
    ld   r5, X+
    ld   r9, -Z
    ld   r8, -Z
    ld   r7, -Z
    ld   r6, -Z
    clr  r19
    clr  r20

    RPS_GROUP r2, r3, r6, r7, r10, r11, r12, r13, r19
    RPS_GROUP r2, r3, r8, r9, r12, r13, r14, r15, r20
    RPS_GROUP r4, r5, r6, r7, r12, r13, r14, r15, r20
    RPS_GROUP r4, r5, r8, r9, r14, r15, r16, r17, r18

    add  r14, r19
    adc  r15, r23
    adc  r16, r20
    adc  r17, r23
    adc  r18, r23
.endm

.macro ADD_PRODUCT_WORD
    ldd  r26, Y+F_PRODUCT_L
    ldd  r27, Y+F_PRODUCT_H
    ld   r2, X+
    ld   r3, X+
    ld   r4, X+
    ld   r5, X+
    std  Y+F_PRODUCT_L, r26
    std  Y+F_PRODUCT_H, r27
    add  r10, r2
    adc  r11, r3
    adc  r12, r4
    adc  r13, r5
    adc  r14, r23
    adc  r15, r23
    adc  r16, r23
    adc  r17, r23
    adc  r18, r23
.endm

.macro SHIFT_ACCUMULATOR
    movw r10, r14
    movw r12, r16
    mov  r14, r18
    clr  r15
    clr  r16
    clr  r17
    clr  r18
.endm

/* r2..r5 = low 32 bits of (r10..r13)*(frame inverse). */
.macro MAKE_QUOTIENT
    ldd  r6, Y+F_INVERSE_0
    ldd  r7, Y+F_INVERSE_1
    ldd  r8, Y+F_INVERSE_2
    ldd  r9, Y+F_INVERSE_3
    clr  r2
    clr  r3
    clr  r4
    clr  r5

    mul  r10, r6
    add  r2, r0
    adc  r3, r1
    adc  r4, r23
    adc  r5, r23
    mul  r10, r7
    add  r3, r0
    adc  r4, r1
    adc  r5, r23
    mul  r10, r8
    add  r4, r0
    adc  r5, r1
    mul  r10, r9
    add  r5, r0

    mul  r11, r6
    add  r3, r0
    adc  r4, r1
    adc  r5, r23
    mul  r11, r7
    add  r4, r0
    adc  r5, r1
    mul  r11, r8
    add  r5, r0

    mul  r12, r6
    add  r4, r0
    adc  r5, r1
    mul  r12, r7
    add  r5, r0

    mul  r13, r6
    add  r5, r0
.endm

.section .text.hspsMontgomeryReduce128,"ax",@progbits
.global hspsMontgomeryReduce128
.type hspsMontgomeryReduce128, @function
hspsMontgomeryReduce128:
    push r2
    push r3
    push r4
    push r5
    push r6
    push r7
    push r8
    push r9
    push r10
    push r11
    push r12
    push r13
    push r14
    push r15
    push r16
    push r17
    push r28
    push r29

    in   r28, _SFR_IO_ADDR(SPL)
    in   r29, _SFR_IO_ADDR(SPH)
    sbiw r28, FRAME_SIZE
    in   r0, _SFR_IO_ADDR(SREG)
    cli
    out  _SFR_IO_ADDR(SPH), r29
    out  _SFR_IO_ADDR(SREG), r0
    out  _SFR_IO_ADDR(SPL), r28

    std  Y+F_OUT_L, r24
    std  Y+F_OUT_H, r25
    std  Y+F_PRODUCT_L, r22
    std  Y+F_PRODUCT_H, r23
    std  Y+F_MODULUS_L, r20
    std  Y+F_MODULUS_H, r21
    std  Y+F_INVERSE_0, r16
    std  Y+F_INVERSE_1, r17
    std  Y+F_INVERSE_2, r18
    std  Y+F_INVERSE_3, r19
    std  Y+F_SCRATCH_L, r14
    std  Y+F_SCRATCH_H, r15
    std  Y+F_POINTER_L, r14
    std  Y+F_POINTER_H, r15
    std  Y+F_COLUMN, r1

    clr  r10
    clr  r11
    clr  r12
    clr  r13
    clr  r14
    clr  r15
    clr  r16
    clr  r17
    clr  r18
    clr  r23

.Llow_column:
    ADD_PRODUCT_WORD
    ldd  r24, Y+F_COLUMN
    tst  r24
    brne .Llow_known_products
    rjmp .Llow_after_known

.Llow_known_products:
    ldd  r26, Y+F_SCRATCH_L
    ldd  r27, Y+F_SCRATCH_H
    ldd  r30, Y+F_MODULUS_L
    ldd  r31, Y+F_MODULUS_H
    mov  r21, r24
    inc  r21
    lsl  r21
    lsl  r21
    add  r30, r21
    adc  r31, r23
    mov  r21, r24
.Llow_rps_loop:
    RPS_BLOCK
    dec  r21
    breq .Llow_after_known
    rjmp .Llow_rps_loop

.Llow_after_known:
    MAKE_QUOTIENT
    ldd  r26, Y+F_POINTER_L
    ldd  r27, Y+F_POINTER_H
    st   X+, r2
    st   X+, r3
    st   X+, r4
    st   X+, r5
    std  Y+F_POINTER_L, r26
    std  Y+F_POINTER_H, r27

    ldd  r30, Y+F_MODULUS_L
    ldd  r31, Y+F_MODULUS_H
    ld   r6, Z+
    ld   r7, Z+
    ld   r8, Z+
    ld   r9, Z+
    clr  r19
    clr  r20
    RPS_GROUP r2, r3, r6, r7, r10, r11, r12, r13, r19
    RPS_GROUP r2, r3, r8, r9, r12, r13, r14, r15, r20
    RPS_GROUP r4, r5, r6, r7, r12, r13, r14, r15, r20
    RPS_GROUP r4, r5, r8, r9, r14, r15, r16, r17, r18
    add  r14, r19
    adc  r15, r23
    adc  r16, r20
    adc  r17, r23
    adc  r18, r23
    SHIFT_ACCUMULATOR

    ldd  r24, Y+F_COLUMN
    inc  r24
    std  Y+F_COLUMN, r24
    cpi  r24, 32
    breq .Llow_done
    rjmp .Llow_column

.Llow_done:
    ldd  r24, Y+F_SCRATCH_L
    ldd  r25, Y+F_SCRATCH_H
    std  Y+F_POINTER_L, r24
    std  Y+F_POINTER_H, r25

.Lhigh_column:
    ADD_PRODUCT_WORD
    ldd  r24, Y+F_COLUMN
    mov  r21, r24
    subi r21, 31
    lsl  r21
    lsl  r21
    ldd  r26, Y+F_SCRATCH_L
    ldd  r27, Y+F_SCRATCH_H
    add  r26, r21
    adc  r27, r23
    ldd  r30, Y+F_MODULUS_L
    ldd  r31, Y+F_MODULUS_H
    subi r30, lo8(-(128))
    sbci r31, hi8(-(128))
    ldi  r21, 63
    sub  r21, r24
.Lhigh_rps_loop:
    RPS_BLOCK
    dec  r21
    breq .Lhigh_rps_done
    rjmp .Lhigh_rps_loop

.Lhigh_rps_done:
    ldd  r26, Y+F_POINTER_L
    ldd  r27, Y+F_POINTER_H
    st   X+, r10
    st   X+, r11
    st   X+, r12
    st   X+, r13
    std  Y+F_POINTER_L, r26
    std  Y+F_POINTER_H, r27
    SHIFT_ACCUMULATOR
    ldd  r24, Y+F_COLUMN
    inc  r24
    std  Y+F_COLUMN, r24
    cpi  r24, 63
    breq .Lhigh_done
    rjmp .Lhigh_column

.Lhigh_done:
    ADD_PRODUCT_WORD
    ldd  r26, Y+F_SCRATCH_L
    ldd  r27, Y+F_SCRATCH_H
    subi r26, lo8(-(124))
    sbci r27, hi8(-(124))
    st   X+, r10
    st   X+, r11
    st   X+, r12
    st   X+, r13
    st   X,  r14

    /* Constant-shape subtraction into scratch, preserving the final borrow. */
    ldd  r26, Y+F_SCRATCH_L
    ldd  r27, Y+F_SCRATCH_H
    ldd  r30, Y+F_MODULUS_L
    ldd  r31, Y+F_MODULUS_H
    ldi  r24, 128
    clc
.Lsubtract_loop:
    ld   r2, X
    ld   r3, Z+
    sbc  r2, r3
    st   X+, r2
    dec  r24
    brne .Lsubtract_loop

    clr  r2
    sbc  r2, r2
    ld   r21, X
    com  r21
    andi r21, 1
    and  r2, r21
    neg  r2

    ldd  r26, Y+F_SCRATCH_L
    ldd  r27, Y+F_SCRATCH_H
    ldd  r30, Y+F_MODULUS_L
    ldd  r31, Y+F_MODULUS_H
    ldi  r24, 128
    clc
.Lrestore_loop:
    ld   r3, X
    ld   r4, Z+
    and  r4, r2
    adc  r3, r4
    st   X+, r3
    dec  r24
    brne .Lrestore_loop
    st   X, r23

    ldd  r26, Y+F_SCRATCH_L
    ldd  r27, Y+F_SCRATCH_H
    ldd  r30, Y+F_OUT_L
    ldd  r31, Y+F_OUT_H
    ldi  r24, 128
.Lcopy_loop:
    ld   r2, X+
    st   Z+, r2
    dec  r24
    brne .Lcopy_loop

    adiw r28, FRAME_SIZE
    in   r0, _SFR_IO_ADDR(SREG)
    cli
    out  _SFR_IO_ADDR(SPH), r29
    out  _SFR_IO_ADDR(SREG), r0
    out  _SFR_IO_ADDR(SPL), r28
    pop  r29
    pop  r28
    pop  r17
    pop  r16
    pop  r15
    pop  r14
    pop  r13
    pop  r12
    pop  r11
    pop  r10
    pop  r9
    pop  r8
    pop  r7
    pop  r6
    pop  r5
    pop  r4
    pop  r3
    pop  r2
    clr  r1
    ret
.size hspsMontgomeryReduce128, .-hspsMontgomeryReduce128
