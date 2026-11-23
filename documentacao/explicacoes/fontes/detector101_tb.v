module tb;
    reg clk = 0, rst, x;
    wire y;
    integer erros = 0;
    seq_detector dut (.clk(clk), .rst(rst), .x(x), .y(y));
    always #5 clk = ~clk;
    task feed(input b, input exp_y);
        begin
            x = b;
            @(posedge clk); #1;
            if (y !== exp_y) begin
                erros = erros + 1;
                $display("[ERRO] x=%b y=%b esperado=%b", b, y, exp_y);
            end
        end
    endtask
    initial begin
        rst = 1; x = 0; @(posedge clk); #1;
        rst = 0;
        feed(1, 0);
        feed(0, 0);
        feed(1, 1);
        feed(1, 0);
        feed(0, 0);
        feed(1, 1);
        if (erros != 0) $fatal(1, "detector: %0d erros", erros);
        $display("[PASSOU] seq_detector 101 ok");
        $finish;
    end
endmodule
