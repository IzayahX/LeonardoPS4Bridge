/* Two-pass 1024-bit Reverse Product Scanning square for ATmega32U4.
 *
 * The first pass writes undoubled off-diagonal 32-bit columns. The second
 * pass doubles those columns and adds each 32-bit diagonal word square.
 * One stack frame keeps the 72-bit accumulator in r2..r10 throughout.
 */

.equ SQUARE_SP_L, 0x3d
.equ SQUARE_SP_H, 0x3e
.equ SQUARE_SREG, 0x3f

.macro RPS_SQUARE_GROUP alo, ahi, blo, bhi, z0, z1, z2, z3, catcher
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

.macro RPS_SQUARE_BLOCK
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

    RPS_SQUARE_GROUP r11, r12, r15, r16, r2, r3, r4, r5, r19
    RPS_SQUARE_GROUP r11, r12, r17, r18, r4, r5, r6, r7, r22
    RPS_SQUARE_GROUP r13, r14, r15, r16, r4, r5, r6, r7, r22
    RPS_SQUARE_GROUP r13, r14, r17, r18, r6, r7, r8, r9, r10

    add  r6, r19
    adc  r7, r23
    adc  r8, r22
    adc  r9, r23
    adc  r10, r23
.endm

.macro DOUBLE_CROSS_ADD diagonal
    ld   r20, Z
    clr  r21
    lsl  r20
    rol  r21
    add  r20, \diagonal
    adc  r21, r23
    add  r20, r25
    adc  r21, r23
    st   Z+, r20
    mov  r25, r21
.endm

.section .text.rpsSquare128,"ax",@progbits
.global rpsSquare128
.type rpsSquare128, @function
rpsSquare128:
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

    in   r28, SQUARE_SP_L
    in   r29, SQUARE_SP_H
    sbiw r28, 8
    in   r0, SQUARE_SREG
    cli
    out  SQUARE_SP_H, r29
    out  SQUARE_SREG, r0
    out  SQUARE_SP_L, r28

    std  Y+1, r24             /* product base */
    std  Y+2, r25
    std  Y+3, r22             /* input base */
    std  Y+4, r23
    clr  r23                  /* permanent zero */
    std  Y+5, r23             /* column */
    clr  r2
    clr  r3
    clr  r4
    clr  r5
    clr  r6
    clr  r7
    clr  r8
    clr  r9
    clr  r10

.Lsquare_cross_column:
    ldd  r24, Y+5
    cpi  r24, 32
    brlo .Lsquare_first_zero
    mov  r25, r24
    subi r25, 31
    rjmp .Lsquare_first_ready
.Lsquare_first_zero:
    clr  r25
.Lsquare_first_ready:
    std  Y+6, r25
    tst  r24
    brne .Lsquare_column_nonzero
    rjmp .Lsquare_cross_done
.Lsquare_column_nonzero:
    mov  r22, r24
    dec  r22
    lsr  r22                  /* last = (column - 1) / 2 */
    cp   r22, r25
    brsh .Lsquare_pairs_present
    rjmp .Lsquare_cross_done
.Lsquare_pairs_present:
    sub  r22, r25
    inc  r22                  /* word-pair count */

    ldd  r26, Y+3
    ldd  r27, Y+4
    mov  r20, r25
    lsl  r20
    lsl  r20
    add  r26, r20
    adc  r27, r23             /* X = input + 4*first */

    ldd  r30, Y+3
    ldd  r31, Y+4
    sub  r24, r25
    inc  r24
    lsl  r24
    lsl  r24
    add  r30, r24
    adc  r31, r23             /* Z = input + 4*(column-first+1) */
    mov  r25, r22
.Lsquare_cross_block:
    RPS_SQUARE_BLOCK
    dec  r25
    breq .Lsquare_cross_done
    rjmp .Lsquare_cross_block

.Lsquare_cross_done:
    ldd  r26, Y+1
    ldd  r27, Y+2
    ldd  r24, Y+5
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

    ldd  r24, Y+5
    inc  r24
    std  Y+5, r24
    cpi  r24, 63
    breq .Lsquare_cross_columns_finished
    rjmp .Lsquare_cross_column
.Lsquare_cross_columns_finished:
    st   X+, r23
    st   X+, r23
    st   X+, r23
    st   X+, r23

    ldd  r26, Y+3
    ldd  r27, Y+4
    ldd  r30, Y+1
    ldd  r31, Y+2
    ldi  r24, 32
    std  Y+5, r24
    clr  r25                  /* carry between 64-bit output chunks */

.Lsquare_diagonal_word:
    clr  r2
    clr  r3
    clr  r4
    clr  r5
    clr  r6
    clr  r7
    clr  r8
    clr  r9
    clr  r10
    ld   r11, X+
    ld   r12, X+
    ld   r13, X+
    ld   r14, X+
    mov  r15, r11
    mov  r16, r12
    mov  r17, r13
    mov  r18, r14
    clr  r19
    clr  r22
    RPS_SQUARE_GROUP r11, r12, r15, r16, r2, r3, r4, r5, r19
    RPS_SQUARE_GROUP r11, r12, r17, r18, r4, r5, r6, r7, r22
    RPS_SQUARE_GROUP r13, r14, r15, r16, r4, r5, r6, r7, r22
    RPS_SQUARE_GROUP r13, r14, r17, r18, r6, r7, r8, r9, r10
    add  r6, r19
    adc  r7, r23
    adc  r8, r22
    adc  r9, r23
    adc  r10, r23

    DOUBLE_CROSS_ADD r2
    DOUBLE_CROSS_ADD r3
    DOUBLE_CROSS_ADD r4
    DOUBLE_CROSS_ADD r5
    DOUBLE_CROSS_ADD r6
    DOUBLE_CROSS_ADD r7
    DOUBLE_CROSS_ADD r8
    DOUBLE_CROSS_ADD r9

    ldd  r24, Y+5
    dec  r24
    std  Y+5, r24
    breq .Lsquare_diagonal_finished
    rjmp .Lsquare_diagonal_word
.Lsquare_diagonal_finished:

    clr  r1
    adiw r28, 8
    in   r0, SQUARE_SREG
    cli
    out  SQUARE_SP_H, r29
    out  SQUARE_SREG, r0
    out  SQUARE_SP_L, r28

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
.size rpsSquare128, .-rpsSquare128
