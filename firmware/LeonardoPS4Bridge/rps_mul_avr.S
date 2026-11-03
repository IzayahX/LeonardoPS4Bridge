/* Single-frame 1024x1024-bit Reverse Product Scanning multiplication. */

.equ MUL_SP_L, 0x3d
.equ MUL_SP_H, 0x3e
.equ MUL_SREG, 0x3f

.macro RPS_MUL_GROUP alo, ahi, blo, bhi, z0, z1, z2, z3, catcher
    mul  \ahi, \bhi
    movw r20, r0

    mul  \alo, \bhi
    add  \z1, r0
    adc  r20, r1
    adc  r21, r23

    mul  \ahi, \blo
    add  \z1, r0
    adc  r20, r1
    adc  r21, r23

    mul  \alo, \blo
    add  \z0, r0
    adc  \z1, r1
    adc  \z2, r20
    adc  \z3, r21
    adc  \catcher, r23
.endm

.macro RPS_MUL_BLOCK
    ld   r11, X+
    ld   r12, X+
    ld   r13, X+
    ld   r14, X+
    ld   r18, -Z
    ld   r17, -Z
    ld   r16, -Z
    ld   r15, -Z
    clr  r19
    clr  r22

    RPS_MUL_GROUP r11, r12, r15, r16, r2, r3, r4, r5, r19
    RPS_MUL_GROUP r11, r12, r17, r18, r4, r5, r6, r7, r22
    RPS_MUL_GROUP r13, r14, r15, r16, r4, r5, r6, r7, r22
    RPS_MUL_GROUP r13, r14, r17, r18, r6, r7, r8, r9, r10

    add  r6, r19
    adc  r7, r23
    adc  r8, r22
    adc  r9, r23
    adc  r10, r23
.endm

.section .text.rpsMultiply128,"ax",@progbits
.global rpsMultiply128
.type rpsMultiply128, @function
rpsMultiply128:
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

    in   r28, MUL_SP_L
    in   r29, MUL_SP_H
    sbiw r28, 7
    in   r0, MUL_SREG
    cli
    out  MUL_SP_H, r29
    out  MUL_SREG, r0
    out  MUL_SP_L, r28

    std  Y+1, r24             /* product base */
    std  Y+2, r25
    std  Y+3, r22             /* A base */
    std  Y+4, r23
    std  Y+5, r20             /* B base */
    std  Y+6, r21
    clr  r23                  /* permanent zero */
    std  Y+7, r23             /* column */
    clr  r2
    clr  r3
    clr  r4
    clr  r5
    clr  r6
    clr  r7
    clr  r8
    clr  r9
    clr  r10

.Lmul_column:
    ldd  r24, Y+7
    cpi  r24, 32
    brlo .Lmul_lower_half
    mov  r25, r24
    subi r25, 31              /* first = column - 31 */
    ldi  r22, 32
    sub  r22, r25             /* count = 32 - first */
    ldi  r24, 32              /* reverse end is always B + 128 */
    rjmp .Lmul_bounds_ready
.Lmul_lower_half:
    clr  r25                  /* first = 0 */
    mov  r22, r24
    inc  r22                  /* count = column + 1 */
    mov  r24, r22             /* reverse end = B + 4*count */
.Lmul_bounds_ready:
    ldd  r26, Y+3
    ldd  r27, Y+4
    mov  r20, r25
    lsl  r20
    lsl  r20
    add  r26, r20
    adc  r27, r23             /* X = A + 4*first */

    ldd  r30, Y+5
    ldd  r31, Y+6
    mov  r20, r24
    lsl  r20
    lsl  r20
    add  r30, r20
    adc  r31, r23             /* Z = B + 4*(last+1) */
    mov  r25, r22

.Lmul_block:
    RPS_MUL_BLOCK
    dec  r25
    breq .Lmul_column_done
    rjmp .Lmul_block

.Lmul_column_done:
    ldd  r26, Y+1
    ldd  r27, Y+2
    ldd  r24, Y+7
    lsl  r24
    lsl  r24
    add  r26, r24
    adc  r27, r23
    st   X+, r2
    st   X+, r3
    st   X+, r4
    st   X+, r5

    mov  r2, r6
    mov  r3, r7
    mov  r4, r8
    mov  r5, r9
    mov  r6, r10
    clr  r7
    clr  r8
    clr  r9
    clr  r10

    ldd  r24, Y+7
    inc  r24
    std  Y+7, r24
    cpi  r24, 63
    breq .Lmul_columns_finished
    rjmp .Lmul_column

.Lmul_columns_finished:
    st   X+, r2
    st   X+, r3
    st   X+, r4
    st   X+, r5

    clr  r1
    adiw r28, 7
    in   r0, MUL_SREG
    cli
    out  MUL_SP_H, r29
    out  MUL_SREG, r0
    out  MUL_SP_L, r28

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
    ret
.size rpsMultiply128, .-rpsMultiply128
