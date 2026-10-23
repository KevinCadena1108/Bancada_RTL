// HDLBits - Shift4  (https://hdlbits.01xz.net/wiki/Shift4)
// Registrador de deslocamento (a direita) de 4 bits:
//  areset = reset assincrono ativo-alto (zera)
//  load   = carrega data[3:0] (sincrono) -- tem prioridade sobre ena
//  ena    = desloca a direita (novo MSB = 0, LSB descartado)
module top_module (
    input        clk,
    input        areset,
    input        load,
    input        ena,
    input  [3:0] data,
    output reg [3:0] q
);
    always @(posedge clk or posedge areset) begin
        if (areset)     q <= 4'b0000;
        else if (load)  q <= data;
        else if (ena)   q <= {1'b0, q[3:1]};
    end
endmodule
