import React from 'react';
import { PipelineStep } from './D3GraphEngine';

export interface GraphControlsProps {
  step: PipelineStep;
  onRunDiscovery?: () => void;
  onIdentifyBottleneck?: () => void;
  onSearchCrossDomain?: () => void;
}

export const GraphControls: React.FC<GraphControlsProps> = ({
  step,
  onRunDiscovery,
  onIdentifyBottleneck,
  onSearchCrossDomain
}) => {
  return (
    <div className="absolute z-10 bg-white border border-[#E5E5E5] p-4 shadow-[4px_4px_0px_rgba(0,0,0,0.05)] text-[13px] top-5 left-5 w-[250px]">
      <button
        onClick={onRunDiscovery}
        disabled={step !== 'idle'}
        className={`w-full border border-[#E0E0E0] font-sans text-[13px] font-semibold py-2 px-3 mb-2 text-center transition-all duration-200 ${
          step !== 'idle'
            ? 'opacity-50 cursor-not-allowed bg-[#FAFAFA] text-[#666]'
            : 'bg-white text-[#666] hover:bg-[#F5F5F5] hover:text-black hover:border-[#CCC] cursor-pointer'
        } ${step === 'simulated' ? 'border-[#3498db] text-[#3498db] bg-[#EBF5FB]' : ''}`}
      >
        Run Discovery
      </button>
      <button
        onClick={onIdentifyBottleneck}
        disabled={step !== 'simulated'}
        className={`w-full border border-[#E0E0E0] font-sans text-[13px] font-semibold py-2 px-3 mb-2 text-center transition-all duration-200 ${
          step !== 'simulated'
            ? 'opacity-50 cursor-not-allowed bg-[#FAFAFA] text-[#666]'
            : 'bg-white text-[#666] hover:bg-[#F5F5F5] hover:text-black hover:border-[#CCC] cursor-pointer'
        } ${step === 'bottleneck' ? 'border-[#C5283D] text-[#C5283D] bg-[#FFF0F5]' : ''}`}
      >
        Identify Bottleneck
      </button>
      <button
        onClick={onSearchCrossDomain}
        disabled={step !== 'bottleneck'}
        className={`w-full border border-[#E0E0E0] font-sans text-[13px] font-semibold py-2 px-3 mb-2 text-center transition-all duration-200 ${
          step !== 'bottleneck'
            ? 'opacity-50 cursor-not-allowed bg-[#FAFAFA] text-[#666]'
            : 'bg-white text-[#666] hover:bg-[#F5F5F5] hover:text-black hover:border-[#CCC] cursor-pointer'
        } ${step === 'crossdomain' ? 'border-[#7B2D8E] text-[#7B2D8E] bg-[#F5EEF8]' : ''}`}
      >
        Search Cross-Domain
      </button>
    </div>
  );
};
