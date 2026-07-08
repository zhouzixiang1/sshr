#include <cstdint>
#include <iostream>
#include <string>

#include <lorina/blif.hpp>

#include <mockturtle/algorithms/cleanup.hpp>
#include <mockturtle/algorithms/node_resynthesis.hpp>
#include <mockturtle/algorithms/node_resynthesis/xag_npn.hpp>
#include <mockturtle/io/blif_reader.hpp>
#include <mockturtle/networks/klut.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/views/depth_view.hpp>

int main( int argc, char** argv )
{
  if ( argc != 2 )
  {
    std::cerr << "usage: " << argv[0] << " input.blif\n";
    return 2;
  }

  const std::string blif_path = argv[1];

  mockturtle::klut_network klut;
  const auto read_result = lorina::read_blif( blif_path, mockturtle::blif_reader( klut ) );
  if ( read_result != lorina::return_code::success )
  {
    std::cerr << "error=read_blif_failed\n";
    return 3;
  }

  const auto cleaned_klut = mockturtle::cleanup_dangling( klut );
  mockturtle::depth_view klut_depth{ cleaned_klut };

  mockturtle::xag_npn_resynthesis<
      mockturtle::xag_network,
      mockturtle::xag_network,
      mockturtle::xag_npn_db_kind::xag_complete>
      resyn;
  const auto raw_xag = mockturtle::node_resynthesis<mockturtle::xag_network>( cleaned_klut, resyn );
  const auto xag = mockturtle::cleanup_dangling( raw_xag );
  mockturtle::depth_view xag_depth{ xag };

  uint32_t xag_and = 0;
  uint32_t xag_xor = 0;
  uint32_t xag_other = 0;
  xag.foreach_gate( [&]( auto const& n ) {
    if ( xag.is_and( n ) )
    {
      ++xag_and;
    }
    else if ( xag.is_xor( n ) )
    {
      ++xag_xor;
    }
    else
    {
      ++xag_other;
    }
  } );

  std::cout << "klut_pis=" << cleaned_klut.num_pis() << "\n";
  std::cout << "klut_pos=" << cleaned_klut.num_pos() << "\n";
  std::cout << "klut_gates=" << cleaned_klut.num_gates() << "\n";
  std::cout << "klut_depth=" << klut_depth.depth() << "\n";
  std::cout << "xag_pis=" << xag.num_pis() << "\n";
  std::cout << "xag_pos=" << xag.num_pos() << "\n";
  std::cout << "xag_gates=" << xag.num_gates() << "\n";
  std::cout << "xag_and=" << xag_and << "\n";
  std::cout << "xag_xor=" << xag_xor << "\n";
  std::cout << "xag_other=" << xag_other << "\n";
  std::cout << "xag_depth=" << xag_depth.depth() << "\n";
  return 0;
}
