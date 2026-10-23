// HDLBits - Mux2to1  (https://hdlbits.01xz.net/wiki/Mux2to1)
// Mux 2-para-1 de 1 bit: sel=0 -> a ; sel=1 -> b.
module top_module (
    input  a,
    input  b,
    input  sel,
    output out
);
    assign out = sel ? b : a;
endmodule
