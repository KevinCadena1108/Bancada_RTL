module tb;
    reg  [31:0] a, b;
    wire [32:0] sum;
    integer erros = 0;

    adder_32bit dut (.a(a), .b(b), .sum(sum));

    initial begin
        a = 5;   b = 3;   #10; if (sum !== 8)   erros = erros + 1;
        a = 100; b = 200; #10; if (sum !== 300) erros = erros + 1;
        a = 0;   b = 0;   #10; if (sum !== 0)   erros = erros + 1;
        if (erros != 0) $fatal(1);
        $finish;
    end
endmodule
