.data
str_in: .asciz "Can #You code #ME in numbers?!"
str_out: .space 32

.text
main:
    la s0, str_in 
    la s1, str_out
    li t1, 1
    li t2, 'A'
    li t3, 'Z'
    li t5, ' '
    
Loop:
    lbu t0, 0(s0)
    beq t0, t5, Reset
    beqz t0, End 
    bgt t0, t3, Store       # if the ascii of t0 is greater than 90
    blt t0, t2, Store       # if the ascii of t0 is less than 65
    andi t4, t1, 1
    beqz t4, Store          # if the index of the character is not odd
    addi t0, t0, 32         # convert the character to lowercase
    j Store                 # IMPORTANT: jump to Store, don't fall through to Reset!
    
Reset:
    li t1, 0
    
Store:
    sb t0, 0(s1)
    addi s0, s0, 1          # increment s0 
    addi s1, s1, 1          # increment s1
    addi t1, t1, 1          # increment counter
    j Loop 
    
End: 
    sb zero, 0(s1)
    li a7, 10
    ecall