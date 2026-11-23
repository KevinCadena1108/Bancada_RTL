`timescale 1ns/1ps
module top_module (
    input  clk,
    input  reset,
    input  w,
    output z
);
    parameter [6:1] A = 6'b000001;
    parameter [6:1] B = 6'b000010;
    parameter [6:1] C = 6'b000100;
    parameter [6:1] D = 6'b001000;
    parameter [6:1] E = 6'b010000;
    parameter [6:1] F = 6'b100000;

    reg [6:1] curr_state;
    reg [6:1] next_state;

    always @(posedge clk) begin
        if (reset)
            curr_state <= A;
        else
            curr_state <= next_state;
    end

    always @(*) begin
        case (curr_state)
            A: next_state = w ? B : A;
            B: next_state = w ? C : D;
            C: next_state = w ? E : D;
            D: next_state = w ? F : A;
            E: next_state = w ? E : D;
            F: next_state = w ? C : D;
            default: next_state = A;
        endcase
    end

    assign z = curr_state[5] | curr_state[6];

endmodule