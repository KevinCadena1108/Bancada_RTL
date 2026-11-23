`timescale 1ns / 1ps

module tb;

    reg clk;
    reg reset;
    reg data;
    reg ack;

    wire [3:0] count;
    wire counting;
    wire done;

    integer tests;
    integer i;

    top_module dut (
        .clk(clk),
        .reset(reset),
        .data(data),
        .count(count),
        .counting(counting),
        .done(done),
        .ack(ack)
    );

    always #5 clk = ~clk;

    task tick;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    task check_outputs;
        input [3:0] expected_count;
        input expected_counting;
        input expected_done;
        begin
            tests = tests + 1;
            if (counting !== expected_counting) begin
                $display("ERRO counting: tempo=%0t obtido=%b esperado=%b count=%h done=%b",
                         $time, counting, expected_counting, count, done);
                $fatal(1);
            end
            if (done !== expected_done) begin
                $display("ERRO done: tempo=%0t obtido=%b esperado=%b count=%h counting=%b",
                         $time, done, expected_done, count, counting);
                $fatal(1);
            end
            if (expected_counting && count !== expected_count) begin
                $display("ERRO count: tempo=%0t obtido=%h esperado=%h counting=%b done=%b",
                         $time, count, expected_count, counting, done);
                $fatal(1);
            end
        end
    endtask

    task apply_reset;
        begin
            reset = 1'b1; data = 1'b0; ack = 1'b0;
            tick; check_outputs(4'h0, 1'b0, 1'b0);
            tick; check_outputs(4'h0, 1'b0, 1'b0);
            reset = 1'b0;
            tick; check_outputs(4'h0, 1'b0, 1'b0);
        end
    endtask

    task send_bit;
        input value;
        begin
            data = value;
            tick; check_outputs(4'h0, 1'b0, 1'b0);
        end
    endtask

    task send_start_sequence_1101;
        begin
            send_bit(1'b1); send_bit(1'b1); send_bit(1'b0); send_bit(1'b1);
        end
    endtask

    task send_wrong_sequence_and_flush;
        begin
            send_bit(1'b1); send_bit(1'b0); send_bit(1'b0); send_bit(1'b1); send_bit(1'b0);
            send_bit(1'b0); send_bit(1'b0); send_bit(1'b0);
        end
    endtask

    task send_delay_bits;
        input [3:0] delay_value;
        begin
            data = delay_value[3]; tick; check_outputs(4'h0, 1'b0, 1'b0);
            data = delay_value[2]; tick; check_outputs(4'h0, 1'b0, 1'b0);
            data = delay_value[1]; tick; check_outputs(4'h0, 1'b0, 1'b0);
            data = delay_value[0]; tick;
            check_outputs(delay_value, 1'b1, 1'b0);
        end
    endtask

    task check_counting_for_1000_cycles;
        input [3:0] expected_count;
        begin
            for (i = 0; i < 1000; i = i + 1) begin
                check_outputs(expected_count, 1'b1, 1'b0);
                tick;
            end
        end
    endtask

    task wait_timer_delay0;
        begin
            check_counting_for_1000_cycles(4'h0);
            check_outputs(4'h0, 1'b0, 1'b1);
        end
    endtask

    task wait_timer_delay1;
        begin
            check_counting_for_1000_cycles(4'h1);
            check_counting_for_1000_cycles(4'h0);
            check_outputs(4'h0, 1'b0, 1'b1);
        end
    endtask

    task acknowledge_done;
        begin
            ack = 1'b0; tick; check_outputs(4'h0, 1'b0, 1'b1);
            ack = 1'b1; tick; check_outputs(4'h0, 1'b0, 1'b0);
            ack = 1'b0; tick; check_outputs(4'h0, 1'b0, 1'b0);
        end
    endtask

    initial begin
        clk = 1'b0; reset = 1'b0; data = 1'b0; ack = 1'b0; tests = 0;

        apply_reset();

        send_wrong_sequence_and_flush();
        check_outputs(4'h0, 1'b0, 1'b0);

        send_start_sequence_1101();
        send_delay_bits(4'h0);
        wait_timer_delay0();

        data = 1'b1; tick; check_outputs(4'h0, 1'b0, 1'b1);
        data = 1'b0; tick; check_outputs(4'h0, 1'b0, 1'b1);
        acknowledge_done();

        send_start_sequence_1101();
        send_delay_bits(4'h1);
        wait_timer_delay1();
        acknowledge_done();

        send_bit(1'b1); send_bit(1'b1);
        reset = 1'b1; tick; check_outputs(4'h0, 1'b0, 1'b0);
        reset = 1'b0; tick; check_outputs(4'h0, 1'b0, 1'b0);

        send_start_sequence_1101();
        send_delay_bits(4'h0);
        wait_timer_delay0();
        acknowledge_done();

        send_start_sequence_1101();
        send_delay_bits(4'h1);
        check_outputs(4'h1, 1'b1, 1'b0);
        tick; check_outputs(4'h1, 1'b1, 1'b0);
        reset = 1'b1; tick; check_outputs(4'h0, 1'b0, 1'b0);
        reset = 1'b0; tick; check_outputs(4'h0, 1'b0, 1'b0);

        $display("Testbench finalizado com sucesso. Testes executados: %0d", tests);
        $finish;
    end

endmodule
