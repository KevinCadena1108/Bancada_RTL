// Harness do Verilator: roda o loop de tempo ate o $finish e grava a cobertura.
// O testbench e' Verilog; o modulo do topo se chama sempre "tb".
// Uso: ./sim <arquivo_de_cobertura>

#include <memory>
#include <string>
#include <verilated.h>
#include "Vtb.h"
#if VM_COVERAGE
#include <verilated_cov.h>
#endif

int main(int argc, char** argv) {
    const std::unique_ptr<VerilatedContext> ctx{new VerilatedContext};
    ctx->commandArgs(argc, argv);
    const std::unique_ptr<Vtb> top{new Vtb{ctx.get()}};

    while (!ctx->gotFinish()) {
        top->eval();
        if (!top->eventsPending()) break;
        ctx->time(top->nextTimeSlot());
    }
    top->final();

#if VM_COVERAGE
    const std::string covfile = (argc > 1) ? argv[1] : "coverage.dat";
    ctx->coveragep()->write(covfile.c_str());
#endif
    return 0;
}
