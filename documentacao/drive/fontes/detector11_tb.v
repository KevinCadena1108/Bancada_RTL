`timescale 1ns/1ps
module tb;
    reg clk, rst, in;
    wire out;
    integer erros = 0;
    top_module dut(.clk(clk), .rst(rst), .in(in), .out(out));
    always #5 clk = ~clk;
    task step; begin @(posedge clk); #1; end endtask
    initial begin
        clk = 0; rst = 1; in = 0; step;
        rst = 0;
        in = 1; step; // S0 -> S1
        if (out !== 1'b0) erros = erros + 1;
        in = 1; step; // S1 -> S2 (viu "11")
        if (out !== 1'b1) erros = erros + 1;
        in = 0; step; // S2 -> S0
        if (out !== 1'b0) erros = erros + 1;
        in = 1; step; // S0 -> S1
        in = 0; step; // S1 -> S0
        if (erros != 0) $fatal(1, "detector: %0d erros", erros);
        $display("[PASSOU] detector 11 ok");
        $finish;
    end
endmodule
