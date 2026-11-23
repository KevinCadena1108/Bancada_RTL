`timescale 1ns/1ps

module top_module(
    input clk,
    input load,
    input [255:0] data,
    output reg [255:0] q
);
    reg [255:0] q_next;
    integer i, j;
    integer i_s, i_a, j_s, j_a;

    always @(*) begin
        for(i = 0; i < 16; i = i + 1)
            for(j = 0; j < 16; j = j + 1)
                begin
                    i_s = (i == 0)  ? 15 : i - 1;
                    j_s = (j == 0)  ? 15 : j - 1;
                    i_a = (i == 15) ? 0  : i + 1;
                    j_a = (j == 15) ? 0  : j + 1;

                    case(q[i_a+j_s*16] + q[i_s+j_a*16] + q[i_s+j_s*16] + q[i_a+j_a*16] +
                         q[i_s+j*16]  + q[i_a+j*16]  + q[i+j_s*16]  + q[i+j_a*16])
                        4'd2:    q_next[i+j*16] = q[i+j*16];
                        4'd3:    q_next[i+j*16] = 1'b1;
                        default: q_next[i+j*16] = 1'b0;
                    endcase
                end
    end

    always @(posedge clk) begin
        if(load)
            q <= data;
        else
            q <= q_next;
    end
endmodule